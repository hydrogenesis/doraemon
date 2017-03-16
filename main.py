#!/usr/bin/env python
# -*-encoding:utf-8-*-

import sys
reload(sys)
sys.setdefaultencoding('UTF8')

import os, re, shutil, time, collections, json, thread, math
import copy
import traceback

from HTMLParser import HTMLParser
from xml.etree import ElementTree as ETree

import itchat
from itchat.content import *

from slacker import Slacker
slack = Slacker('xoxb-153223940192-gEkiKWr8A2O2o6zgyh9HKHvE')
send_key = 'xoxb-154204749857-tjxjzkQhdOXFCcacMiw2rV14'
alienware = False
from slackclient import SlackClient
channel_map = {}
user_map = {}
statistics = {}
total_chats = 0
chat_log = {}
chat_id_map = {}
kChatLogMax=9

def get_channel_name(sc, channel_id):
    if not channel_id in channel_map:
	channel_info=sc.api_call("channels.info",channel=channel_id)
        channel_map[channel_id] = channel_info["channel"]["name"]
    return channel_map[channel_id]

def get_user_name(sc, user_id):
    if not user_id in user_map:
	user_info=sc.api_call("users.info",user=user_id)
        user_map[user_id] = user_info["user"]["name"]
    return user_map[user_id]

def get_reply_str(group_list, chat_id_map, default="", reorder=False):
    if reorder:
        score = {}
        do_sort = True
        cur_index = 0
        for c in group_list:
            if not c in statistics:
                do_sort = False
                break
            score[c] = math.log(total_chats / statistics[c]) * (kChatLogMax - cur_index)
            if cur_index == 0: score[c] += 6
            if cur_index == 1: score[c] += 1.5
            if cur_index == 2: score[c] += 0.5
            cur_index += 1
        if do_sort:
            sorted(group_list, key = lambda c: score[c], reverse=True)
            print group_list
        if default in group_list:
            group_list.remove(default)
            group_list.insert(0, default)
    print default
    if default != "":
        print chat_id_map[default]
    chat_str = ""
    index = 1
    for c in group_list:
        chat_str += '%d: %s '% (index, chat_id_map[c])
        index += 1
    return chat_str

def autoreply(thread_name, sc, chat_log, chat_id_map, bot):
    CHANNEL_NAME = "test"
    myself = "U4H6HDF32"
    last_chat = {}
    default = {}
    last_message = ""
    # Connect to slack
    if sc.rtm_connect():
        # Send first message
        sc.rtm_send_message(CHANNEL_NAME, "I'm ALIVE!!!")
        #join_all_channels(sc)

        print 'connected'
        while True:
            # Read latest messages
            for slack_message in sc.rtm_read():
                try:
                    message = slack_message.get("text")
                    user = slack_message.get("user")
                    channel = slack_message.get("channel")
                    if not message or not user or not channel:
                        continue
                    if user != myself:
                        continue
                    channel_short_name = get_channel_name(sc, channel)
                    channel_name = "#" + channel_short_name
                    if not channel_name in last_chat:
                        last_chat[channel_name] = []
                    #print user, message, get_channel_name(sc, channel)
                    if len(last_chat[channel_name]) == 0:
                        chat = copy.deepcopy(chat_log)
                        if not channel_name in chat:
                            sc.rtm_send_message(channel_short_name, "your channel '%s' is not active" %(channel_name))
                            continue
                        if len(chat[channel_name]) == 0:
                            if not channel_name in default:
                                sc.rtm_send_message(channel_short_name, "your message in channel '%s' refers to no one" %(channel_name))
                                continue
                        unique_chat = {}
                        last_chat[channel_name] = []
                        chat[channel_name].reverse()
                        for c in chat[channel_name]:
                            if c in unique_chat: continue
                            unique_chat[c] = 0
                            last_chat[channel_name].append(c)
                        d = ""
                        if channel_name in default:
                            d = default[channel_name]
                        chat_str = get_reply_str(last_chat[channel_name], chat_id_map, d, True)
                        print 'replying to ', channel_short_name, chat_str
                        last_message = message
                        sc.rtm_send_message(channel_short_name, chat_str)
                    else:
                        if message.isdigit() and int(message) <= len(last_chat[channel_name]) and int(message) > 0:
                            message_to_send = last_message
                            destination = last_chat[channel_name][int(message) - 1]
                            default[channel_name] = destination
                            print json.dumps(default, indent=None).decode('unicode-escape').encode('utf8')
                            sc.rtm_send_message(channel_short_name, 'sending message "%s" to "%s"' %(message_to_send, chat_id_map[destination]))
                            #print json.dumps(chat_id_map, indent=None).decode('unicode-escape').encode('utf8')
                            #print chat_id_map[destination]
                            bot.send(message_to_send, toUserName=destination)
                            clear_timeouted_message()
                            last_chat[channel_name] = []
                            last_message = ""
                        elif message == '0':
                            if channel_name in default: del default[channel_name]
                            last_chat[channel_name] = []
                            last_message = ""
                            sc.rtm_send_message(channel_short_name, 'reset all')
                        else:
                            sc.rtm_send_message(channel_short_name, get_reply_str(last_chat[channel_name], chat_id_map))
                    continue
                except Exception, e:
                    print 'exception'
                    traceback.print_exc()
                    continue
                #sc.rtm_send_message(CHANNEL_NAME, "<@%s> %s wrote %s on %s" %(user, get_user_name(sc, user), message, get_channel_name(sc, channel)))
            # Sleep for half a second
            time.sleep(0.5)

msg_store = collections.OrderedDict()
timeout = 600
sending_type = {'Picture': 'img', 'Video': 'vid'}
data_path = 'data'
nickname = ''
bot = None
blacklist = []
channel_mapping = {}

if __name__ == '__main__':
    if not os.path.exists(data_path):
        os.mkdir(data_path)
    # if the QR code doesn't show correctly, you can try to change the value
    # of enableCdmQR to 1 or -1 or -2. It nothing works, you can change it to
    # enableCmdQR=True and a picture will show up.
    with open('blacklist.txt', 'r') as f:
        for line in f:
            blacklist.append(line.strip())
    bot = itchat.new_instance()
    enable_qr = 2
    if alienware: enable_qr = 1
    bot.auto_login(hotReload=True, enableCmdQR=enable_qr)
    nickname = bot.loginInfo['User']['NickName']
    sc = SlackClient(send_key)
    thread.start_new_thread(autoreply, ("AutoReply", sc, chat_log, chat_id_map, bot))

def blacklisted(groupname):
    for i in blacklist:
        if groupname.find(i) != -1: return True
    return False

def clear_timeouted_message():
    now = time.time()
    count = 0
    for k, v in msg_store.items():
        if now - v['ReceivedTime'] > timeout:
            count += 1
        else:
            break
    for i in range(count):
        item = msg_store.popitem(last=False)

def get_channel(receiver, groupchat):
    if groupchat:
        if receiver in channel_mapping:
            return channel_mapping[receiver]
        else:
            return '#general'
    else:
        return '#single'
    
def get_sender_receiver(msg):
    sender = nickname
    receiver = nickname
    sender_id = msg['FromUserName']
    receiver_id = msg['ToUserName']
    groupchat = False
    if msg['FromUserName'][0:2] == '@@': # group chat
        groupchat = True
        sender = msg['ActualNickName']
        m = bot.search_chatrooms(userName=msg['FromUserName'])
        if m is not None:
            receiver = m['NickName']
    elif msg['ToUserName'][0:2] == '@@': # group chat by myself
        groupchat = True
        sender_id = msg['ToUserName']
        receiver_id = msg['FromUserName']
        if 'ActualNickName' in msg:
            sender = msg['ActualNickName']
        else:
            m = bot.search_friends(userName=msg['FromUserName'])
            if m is not None:
                sender = m['NickName']
        m = bot.search_chatrooms(userName=msg['ToUserName'])
        if m is not None:
            receiver = m['NickName']
    else: # personal chat
        m = bot.search_friends(userName=msg['FromUserName'])
        if m is not None:
            sender = m['NickName']
        m = bot.search_friends(userName=msg['ToUserName'])
        if m is not None:
            receiver = m['NickName']
    return HTMLParser().unescape(sender), HTMLParser().unescape(receiver), sender_id, receiver_id, groupchat

def print_msg(msg):
    #msg_str = json.dumps(msg).decode('unicode-escape').encode('utf8')
    msg_str = " ".join(msg)
    print msg_str
    return msg_str

def format_msg(sender, receiver, content, groupchat):
    if groupchat:
        return '[%s] %s: %s' % (receiver, sender, content)
    else:
        if sender == '田甲':
            return '-> %s: %s' % (receiver, content)
        else:
            return '%s: %s' % (sender, content)
    
def get_whole_msg(msg, download=False):
    sender, receiver, sender_id, receiver_id, groupchat = get_sender_receiver(msg)
    if len(msg['FileName']) > 0 and len(msg['Url']) == 0:
        if download: # download the file into data_path directory
            fn = os.path.join(data_path, msg['FileName'])
            msg['Text'](fn)
            if not fn.endswith('.gif'):
                slack_upload = fn
                print 'uploading', slack_upload
                if groupchat:
                    channel = "#general"
                else:
                    channel = "#single"
                if not blacklisted(receiver):
                    slack.files.upload(slack_upload, channels=channel)
            c = '@%s@%s' % (sending_type.get(msg['Type'], 'fil'), fn)
        else:
            c = '@%s@%s' % (sending_type.get(msg['Type'], 'fil'), msg['FileName'])
        return [format_msg(sender, receiver, "", groupchat), c]
    c = msg['Text']
    if len(msg['Url']) > 0:
        url = msg['Url']
        try: # handle map label
            content_tree = ETree.fromstring(msg['OriContent'])
            if content_tree is not None:
                map_label = content_tree.find('location')
                if map_label is not None:
                    c += ' ' + map_label.attrib['poiname']
                    c += ' ' + map_label.attrib['label']
            url = HTMLParser().unescape(msg['Url'])
        except:
            pass
        c += ' ' + url
    return [format_msg(sender, receiver, c, groupchat)]

@bot.msg_register([TEXT, PICTURE, MAP, CARD, SHARING, RECORDING,
    ATTACHMENT, VIDEO, FRIENDS], isFriendChat=True, isGroupChat=True)
def normal_msg(msg):
    whole_msg=get_whole_msg(msg, True)
    msg_log = print_msg(whole_msg)
    sender, receiver, sender_id, receiver_id, groupchat = get_sender_receiver(msg)
    if not blacklisted(receiver):
        if groupchat:
            if not sender_id in statistics:
                statistics[sender_id] = 1
            else:
                statistics[sender_id] += 1
            global total_chats
            total_chats += 1
            channel = "#general"
            if not channel in chat_log:
                chat_log[channel] = []
            chat_id_map[sender_id] = receiver
            while sender_id in chat_log[channel]:
                chat_log[channel].remove(sender_id)
            chat_log[channel].append(sender_id)
            #print json.dumps(statistics, indent=None).decode('unicode-escape').encode('utf8')
        else:
            channel = "#single"
            if not channel in chat_log:
                chat_log[channel] = []
            if sender != "田甲":
                chat_id_map[sender_id] = sender
                while sender_id in chat_log[channel]:
                    chat_log[channel].remove(sender_id)
                chat_log[channel].append(sender_id)
        if len(chat_log[channel]) > kChatLogMax:
            del chat_log[channel][0]
        #print json.dumps(chat_log, indent=None).decode('unicode-escape').encode('utf8')
        slack.chat.post_message(channel, msg_log)

    now = time.time()
    msg['ReceivedTime'] = now
    msg_id = msg['MsgId']
    msg_store[msg_id] = msg
    clear_timeouted_message()

@bot.msg_register([NOTE], isFriendChat=True, isGroupChat=True)
def note_msg(msg):
    whole_msg=get_whole_msg(msg, True)
    print_msg(whole_msg)
    content = None
    content_tree = None
    try:
        content = HTMLParser().unescape(msg['Content'])
        content_tree = ETree.fromstring(content)
    except:
        pass
    if content_tree is None:
        return
    revoked = content_tree.find('revokemsg')
    if revoked is None:
        return
    old_msg_id = revoked.find('msgid').text
    old_msg = msg_store.get(old_msg_id)
    if old_msg is None:
        return
    msg_send = get_whole_msg(old_msg, download=True)
    for m in msg_send:
        bot.send(m, toUserName='filehelper')
    clear_timeouted_message()

if __name__ == '__main__':
    bot.run()
