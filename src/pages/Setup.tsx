import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Icon from "@/components/ui/icon";
import { useToast } from "@/hooks/use-toast";

export default function Setup() {
  const { toast } = useToast();
  const [copied, setCopied] = useState<string | null>(null);

  const copyToClipboard = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopied(id);
    toast({
      title: "Скопировано!",
      description: "Текст скопирован в буфер обмена",
    });
    setTimeout(() => setCopied(null), 2000);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-4xl py-8 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-white">⚙️ Настройка Yandex Cloud</h1>
          <p className="text-slate-300">Пошаговая инструкция по настройке БД и секретов</p>
        </div>

        {/* Шаг 1: База данных */}
        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <span className="bg-blue-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">1</span>
              Создание базы данных PostgreSQL
            </CardTitle>
            <CardDescription className="text-slate-300">
              Managed PostgreSQL (рекомендуется) или PostgreSQL на VM
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-slate-900/50 rounded-lg p-4 space-y-3">
              <h3 className="text-white font-semibold">Вариант A: Managed PostgreSQL (проще)</h3>
              <ol className="list-decimal list-inside space-y-2 text-slate-300 text-sm">
                <li>Открой <a href="https://console.cloud.yandex.ru/" target="_blank" className="text-blue-400 hover:underline">Yandex Cloud Console</a></li>
                <li>Перейди в <strong className="text-white">Managed Service for PostgreSQL</strong></li>
                <li>Нажми <strong className="text-white">"Создать кластер"</strong></li>
                <li>Настройки:
                  <ul className="list-disc list-inside ml-4 mt-1 space-y-1">
                    <li>Имя: <code className="bg-slate-800 px-1 rounded">rsya-db</code></li>
                    <li>Версия: PostgreSQL 14 или 15</li>
                    <li>Класс: <code className="bg-slate-800 px-1 rounded">s2.micro</code> (минимальный)</li>
                    <li>Диск: SSD, 10 GB</li>
                    <li>База данных: <code className="bg-slate-800 px-1 rounded">rsya_cleaner</code></li>
                    <li>Пользователь: <code className="bg-slate-800 px-1 rounded">rsya_user</code></li>
                    <li>Пароль: придумай надёжный (сохрани!)</li>
                    <li>Хост: включи публичный доступ</li>
                  </ul>
                </li>
                <li>После создания скопируй <strong className="text-white">FQDN хоста</strong> (например: <code className="bg-slate-800 px-1 rounded">c-xxx.rw.mdb.yandexcloud.net</code>)</li>
              </ol>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 space-y-3">
              <h3 className="text-white font-semibold">Вариант B: PostgreSQL на VM (дешевле)</h3>
              <ol className="list-decimal list-inside space-y-2 text-slate-300 text-sm">
                <li>Создай VM через деплойер (кнопка "Создать VM")</li>
                <li>Подключись по SSH: <code className="bg-slate-800 px-1 rounded">ssh ubuntu@IP_АДРЕС</code></li>
                <li>Выполни команды:
                  <pre className="bg-slate-950 p-3 rounded mt-2 text-xs overflow-x-auto">
{`sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib
sudo systemctl start postgresql
sudo systemctl enable postgresql

sudo -u postgres psql <<EOF
CREATE DATABASE rsya_cleaner;
CREATE USER rsya_user WITH PASSWORD 'ТВОЙ_ПАРОЛЬ';
GRANT ALL PRIVILEGES ON DATABASE rsya_cleaner TO rsya_user;
\\q
EOF

sudo nano /etc/postgresql/14/main/postgresql.conf
# Раскомментируй: listen_addresses = '*'

sudo nano /etc/postgresql/14/main/pg_hba.conf
# Добавь в конец: host    all    all    0.0.0.0/0    md5

sudo systemctl restart postgresql
sudo ufw allow 5432/tcp`}
                  </pre>
                </li>
              </ol>
            </div>

            <div className="bg-blue-950/30 border border-blue-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Icon name="Info" className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-200">
                  <p className="font-semibold mb-1">Формат DATABASE_URL:</p>
                  <p className="font-mono text-xs bg-slate-900/50 p-2 rounded">
                    postgresql://rsya_user:ПАРОЛЬ@ХОСТ:ПОРТ/rsya_cleaner?sslmode=require
                  </p>
                  <p className="mt-2 text-xs text-blue-300">
                    Для Managed PostgreSQL порт: <code>6432</code>, для VM: <code>5432</code>
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Шаг 2: GitHub токен */}
        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <span className="bg-purple-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">2</span>
              GitHub Personal Access Token
            </CardTitle>
            <CardDescription className="text-slate-300">
              Нужен для чтения репозиториев и обновления func2url.json
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <ol className="list-decimal list-inside space-y-2 text-slate-300 text-sm">
              <li>Открой <a href="https://github.com/settings/tokens" target="_blank" className="text-blue-400 hover:underline">GitHub Settings → Developer settings → Personal access tokens</a></li>
              <li>Нажми <strong className="text-white">"Generate new token (classic)"</strong></li>
              <li>Название: <code className="bg-slate-800 px-1 rounded">Yandex Cloud Deployer</code></li>
              <li>Срок действия: выбери нужный (например, 90 дней или "No expiration")</li>
              <li>Права: отметь <strong className="text-white">repo</strong> (полный доступ к репозиториям)</li>
              <li>Нажми <strong className="text-white">"Generate token"</strong></li>
              <li><strong className="text-red-400">ВАЖНО:</strong> Скопируй токен сразу! Он больше не будет показан.</li>
            </ol>
          </CardContent>
        </Card>

        {/* Шаг 3: Yandex Cloud токен */}
        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <span className="bg-orange-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">3</span>
              Yandex Cloud OAuth токен (YANDEX_CLOUD_TOKEN)
            </CardTitle>
            <CardDescription className="text-slate-300">
              Нужен для работы с API Yandex Cloud (создание VM, функций и т.д.)
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-blue-950/30 border border-blue-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Icon name="Info" className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-blue-200">
                  <p className="font-semibold mb-2">📋 Как получить токен:</p>
                  <div className="space-y-2 text-xs">
                    <div className="bg-green-900/30 border border-green-500/30 rounded p-2">
                      <p className="text-green-200 font-semibold mb-1">✅ Получить IAM токен из Yandex Cloud Console</p>
                      <ol className="list-decimal list-inside space-y-1 text-green-200">
                        <li>Открой <a href="https://console.cloud.yandex.ru/" target="_blank" className="text-green-300 hover:underline font-semibold">Yandex Cloud Console</a></li>
                        <li>В правом верхнем углу нажми на свой аккаунт (аватар или имя)</li>
                        <li>В выпадающем меню найди <strong className="text-white">"Получить IAM токен"</strong> или <strong className="text-white">"Создать токен"</strong></li>
                        <li>Нажми и скопируй токен — это и есть <code className="bg-green-900/50 px-1 rounded">YANDEX_CLOUD_TOKEN</code></li>
                      </ol>
                      <p className="text-green-300 text-xs mt-2">
                        💡 Это самый простой способ! Токен работает сразу и не требует дополнительных настроек.
                      </p>
                    </div>
                    <div className="bg-slate-900/50 rounded p-2">
                      <p className="text-slate-300 text-xs">
                        ℹ️ <strong>Про ключ сервисного аккаунта:</strong> Ключ сервисного аккаунта (ID + секрет) можно использовать для других задач, но для функций деплойера проще использовать IAM токен из консоли.
                      </p>
                    </div>
                    <p className="text-yellow-200 text-xs mt-2">
                      ⚠️ <strong>ВАЖНО:</strong> Скопируй токен сразу! Он больше не будет показан
                    </p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-slate-900/50 rounded-lg p-3">
              <p className="text-slate-300 text-xs mb-2">💡 Где использовать:</p>
              <ul className="list-disc list-inside space-y-1 text-xs text-slate-400">
                <li>Функция <code className="bg-slate-800 px-1 rounded">setup-database</code></li>
                <li>Функция <code className="bg-slate-800 px-1 rounded">vm-setup</code></li>
                <li>Функция <code className="bg-slate-800 px-1 rounded">deploy-functions</code></li>
                <li>Функция <code className="bg-slate-800 px-1 rounded">yc-sync</code></li>
              </ul>
            </div>
            
            <div className="bg-yellow-950/30 border border-yellow-500/30 rounded-lg p-3">
              <div className="flex items-start gap-2">
                <Icon name="AlertTriangle" className="h-4 w-4 text-yellow-400 flex-shrink-0 mt-0.5" />
                <p className="text-yellow-200 text-xs">
                  ⚠️ Токен действует ограниченное время (обычно 1 год). Если истёк — получи новый.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Шаг 4: Настройка секретов в функциях */}
        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <span className="bg-green-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">4</span>
              Настройка переменных окружения в функциях
            </CardTitle>
            <CardDescription className="text-slate-300">
              Добавь секреты в каждую облачную функцию
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-slate-900/50 rounded-lg p-4">
              <p className="text-slate-300 text-sm mb-4">
                Для каждой функции открой её в <a href="https://console.cloud.yandex.ru/functions" target="_blank" className="text-blue-400 hover:underline">Yandex Cloud Console</a>:
              </p>
              
              <div className="space-y-3">
                {[
                  { name: 'deploy-long', env: ['DATABASE_URL', 'GITHUB_TOKEN', 'MAIN_DB_SCHEMA'], desc: 'Деплой фронтенда' },
                  { name: 'deploy-functions', env: ['GITHUB_TOKEN', 'YANDEX_CLOUD_TOKEN'], desc: 'Деплой backend функций' },
                  { name: 'migrate', env: ['DATABASE_URL', 'GITHUB_TOKEN'], desc: 'Применение миграций' },
                  { name: 'deploy-config', env: ['DATABASE_URL', 'MAIN_DB_SCHEMA'], desc: 'Управление конфигами' },
                  { name: 'vm-setup', env: ['DATABASE_URL', 'YANDEX_CLOUD_TOKEN', 'MAIN_DB_SCHEMA'], desc: 'Создание VM' },
                  { name: 'vm-list', env: ['DATABASE_URL', 'MAIN_DB_SCHEMA'], desc: 'Список VM' },
                  { name: 'yc-sync', env: ['DATABASE_URL', 'YANDEX_CLOUD_TOKEN', 'MAIN_DB_SCHEMA'], desc: 'Синхронизация VM' },
                  { name: 'deploy-status', env: ['DATABASE_URL', 'MAIN_DB_SCHEMA'], desc: 'Статус деплоя' },
                ].map((func) => (
                  <div key={func.name} className="bg-slate-800/50 rounded p-3">
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="text-white font-semibold">{func.name}</div>
                        <div className="text-xs text-slate-400">{func.desc}</div>
                        <div className="mt-2 space-y-1">
                          {func.env.map((envVar) => (
                            <div key={envVar} className="text-xs text-slate-300">
                              <code className="bg-slate-900 px-1 rounded">{envVar}</code>
                              {envVar === 'MAIN_DB_SCHEMA' && (
                                <span className="text-slate-500 ml-2">(опционально, по умолчанию: public)</span>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                      <Button
                        size="sm"
                        variant="outline"
                        className="border-blue-500/50 text-blue-300 hover:bg-blue-950/50"
                        onClick={() => {
                          const url = `https://console.cloud.yandex.ru/functions`;
                          window.open(url, '_blank');
                        }}
                      >
                        <Icon name="ExternalLink" className="h-3 w-3 mr-1" />
                        Открыть
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-yellow-950/30 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Icon name="AlertTriangle" className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-yellow-200">
                  <p className="font-semibold mb-1">Как добавить переменные:</p>
                  <ol className="list-decimal list-inside space-y-1 text-xs">
                    <li>Открой функцию → <strong>Версии</strong> → выбери последнюю версию</li>
                    <li>Нажми <strong>Редактировать</strong></li>
                    <li>В разделе <strong>Переменные окружения</strong> добавь нужные ключи и значения</li>
                    <li>Сохрани версию</li>
                  </ol>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Шаг 5: Проверка */}
        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <span className="bg-emerald-600 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm font-bold">5</span>
              Проверка настройки
            </CardTitle>
            <CardDescription className="text-slate-300">
              Убедись что всё работает
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-slate-900/50 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Icon name="CheckCircle" className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-slate-300">
                  <p className="font-semibold text-white mb-2">1. Проверь подключение к БД:</p>
                  <pre className="bg-slate-950 p-2 rounded text-xs overflow-x-auto">
{`psql "postgresql://rsya_user:ПАРОЛЬ@ХОСТ:ПОРТ/rsya_cleaner?sslmode=require"`}
                  </pre>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Icon name="CheckCircle" className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-slate-300">
                  <p className="font-semibold text-white mb-2">2. В деплойере нажми "Применить миграции БД":</p>
                  <p className="text-xs text-slate-400">Должна создаться таблица <code className="bg-slate-800 px-1 rounded">schema_migrations</code></p>
                </div>
              </div>
            </div>

            <div className="bg-slate-900/50 rounded-lg p-4 space-y-3">
              <div className="flex items-start gap-3">
                <Icon name="CheckCircle" className="h-5 w-5 text-green-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-slate-300">
                  <p className="font-semibold text-white mb-2">3. Проверь деплой функций:</p>
                  <p className="text-xs text-slate-400">Нажми "Деплой backend-функций" → должно работать без ошибок</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="flex justify-center gap-3">
          <Button
            onClick={() => window.location.href = '/deploy'}
            className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white"
          >
            <Icon name="ArrowLeft" className="mr-2 h-4 w-4" />
            Вернуться к деплойеру
          </Button>
        </div>
      </div>
    </div>
  );
}
