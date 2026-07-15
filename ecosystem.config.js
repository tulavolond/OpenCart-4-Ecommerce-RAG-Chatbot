module.exports = {
  apps: [{
    name: 'watermark-png',
    // Указываем полный путь к Python из виртуального окружения
    script: '/home/pi/watermark-png/.venv/bin/uvicorn',
    args: 'main:app --host 0.0.0.0 --port 5000 --reload',
    cwd: '/home/pi/watermark-png',
    // Явно указываем интерпретатор
    interpreter: '/home/pi/watermark-png/.venv/bin/python',
    // Или так:
    // exec_interpreter: 'python',
    env: {
      PYTHONUNBUFFERED: '1',
      PATH: '/home/pi/watermark-png/.venv/bin:/usr/local/bin:/usr/bin:/bin'
    },
    error_file: '/home/pi/watermark-png/logs/err.log',
    out_file: '/home/pi/watermark-png/logs/out.log',
    log_file: '/home/pi/watermark-png/logs/combined.log',
    time: true,
    watch: false,
    instances: 1,
    exec_mode: 'fork',
    kill_timeout: 5000,
    max_restarts: 10
  }]
};
