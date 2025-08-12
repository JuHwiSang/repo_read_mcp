#!/bin/bash
seagoat-server start repo > /tmp/seagoat.log 2>&1 &
pid=$!

# 최대 5분 대기하며 완료 문구 감시
timeout 300 bash -c '
  until grep -q "Analyzed all chunks!" /tmp/seagoat.log; do cat /tmp/seagoat.log; sleep 1; done
'

# 깔끔하게 종료
kill -TERM "$pid" || true
wait "$pid" || true