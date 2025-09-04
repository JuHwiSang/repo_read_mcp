#!/bin/bash
seagoat-server start . > /tmp/seagoat.log 2>&1 &
pid=$!

# 최대 20분 대기하며 완료 문구 감시
timeout 1200 bash -c '
  until grep -q "Analyzed all chunks!" /tmp/seagoat.log; do sleep 1; done
'

# 깔끔하게 종료
# kill -TERM "$pid" || true
# wait "$pid" || true
seagoat-server stop .