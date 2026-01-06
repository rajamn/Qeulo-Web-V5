#!/bin/bash
# ============================================================
# 🟢 EB Remote Django Command Runner
# Usage: ./ebrun.sh <django_command> [args...]
# Example: ./ebrun.sh migrate
#          ./ebrun.sh createsuperuser
#          ./ebrun.sh seed_reg
# ============================================================

CMD="$@"

if [ -z "$CMD" ]; then
  echo "Usage: ./ebrun.sh <django_command> [args...]"
  exit 1
fi

echo "🔹 Running: python3 manage.py $CMD on Elastic Beanstalk..."
eb ssh --command "source /var/app/venv/*/bin/activate && cd /var/app/current && python3 manage.py $CMD"
