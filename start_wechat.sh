#!/bin/bash
while true; do
  now=`date +%Y%m%d_%H%M%S`
  ( cd log && ln -sf message_${now}.log latest.log )
  python main.py log/message_${now}.log
done
