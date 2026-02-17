import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import Icon from '@/components/ui/icon';
import { toast } from 'sonner';
import { API_ENDPOINTS } from '@/lib/api';

export default function Migrate() {
  const [file, setFile] = useState<File | null>(null);
  const [githubRepo, setGithubRepo] = useState('');
  const [schemaFrom, setSchemaFrom] = useState('t_p90119217_django_layout_develo');
  const [schemaTo, setSchemaTo] = useState('public');
  const [tableReplaces, setTableReplaces] = useState('{"site_content": "editable_content"}');
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);
  const [result, setResult] = useState<any>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.name.endsWith('.zip')) {
      setFile(selectedFile);
      setLogs([]);
      setResult(null);
    } else {
      toast.error('Выберите ZIP файл');
    }
  };

  const handleMigrateFromGitHub = async () => {
    if (!githubRepo.trim()) {
      toast.error('Укажи репозиторий GitHub (например: username/repo-name)');
      return;
    }

    setLoading(true);
    setLogs(['Применение миграций из GitHub...']);
    setResult(null);

    try {
      const body: Record<string, string | object> = { github_repo: githubRepo.trim() };
      if (schemaFrom.trim()) body.schema_from = schemaFrom.trim();
      if (schemaTo.trim()) body.schema_to = schemaTo.trim();
      try {
        if (tableReplaces.trim()) body.table_replaces = JSON.parse(tableReplaces.trim());
      } catch {
        // ignore invalid JSON
      }
      const response = await fetch(API_ENDPOINTS.migrate, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json().catch(() => ({}));

      if (data.success) {
        setLogs(data.logs || []);
        setResult(data);
        toast.success('Миграции применены!');
      } else {
        const errMsg = data.error || `HTTP ${response.status}`;
        const serverLogs = Array.isArray(data.logs) ? data.logs : [];
        setLogs(prev => [...prev, `Ответ: ${response.status}`, `Ошибка: ${errMsg}`, ...serverLogs]);
        toast.error(errMsg);
      }
    } catch (error: any) {
      const msg = error?.message || String(error);
      setLogs(prev => [...prev, `Сетевая ошибка: ${msg}. Проверь CORS и доступность функции.`]);
      toast.error('Ошибка миграции');
    } finally {
      setLoading(false);
    }
  };

  const handleMigrate = async () => {
    if (!file) {
      toast.error('Выберите файл');
      return;
    }

    setLoading(true);
    setLogs(['Загрузка файла...']);

    try {
      const reader = new FileReader();
      reader.onload = async (e) => {
        const base64 = e.target?.result as string;
        const base64Data = base64.split(',')[1];

        setLogs(prev => [...prev, 'Отправка на сервер...']);

        const response = await fetch(API_ENDPOINTS.migrate, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            zip_file: base64Data
          })
        });

        const data = await response.json();

        if (data.success) {
          setLogs(data.logs || []);
          setResult(data);
          toast.success('Миграция завершена!');
        } else {
          setLogs(prev => [...prev, `Ошибка: ${data.error}`]);
          toast.error(data.error || 'Ошибка миграции');
        }
        
        setLoading(false);
      };

      reader.onerror = () => {
        toast.error('Ошибка чтения файла');
        setLoading(false);
      };

      reader.readAsDataURL(file);
    } catch (error: any) {
      setLogs(prev => [...prev, `Ошибка: ${error.message}`]);
      toast.error('Ошибка миграции');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-white">Миграция проекта</h1>
          <p className="text-slate-300">Примени миграции из GitHub или загрузи ZIP из poehali.dev</p>
        </div>

        {/* Применение миграций из GitHub — без ZIP */}
        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white">Применить миграции из GitHub</CardTitle>
            <CardDescription className="text-slate-300">
              Укажи репозиторий с папкой db_migrations (SQL файлы). ZIP не нужен.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-lg bg-amber-500/10 border border-amber-500/30 p-3 text-sm text-amber-200/90">
              <p className="font-medium mb-1">Если миграции не срабатывают, проверь:</p>
              <ul className="list-disc list-inside space-y-0.5 text-amber-200/80">
                <li>Репозиторий указан верно: <code className="bg-black/30 px-1 rounded">владелец/имя-репо</code> (например твой форк с папкой db_migrations)</li>
                <li>У функции <strong>migrate</strong> в Yandex Cloud заданы переменные: <code className="bg-black/30 px-1 rounded">DATABASE_URL</code>, <code className="bg-black/30 px-1 rounded">GITHUB_TOKEN</code> (для приватного репо — токен с правами repo)</li>
                <li>В репо есть папка <code className="bg-black/30 px-1 rounded">db_migrations</code> с файлами <code className="bg-black/30 px-1 rounded">*.sql</code></li>
              </ul>
            </div>
            <div>
              <Label className="text-slate-300">Репозиторий GitHub</Label>
              <Input
                placeholder="username/repo-name"
                value={githubRepo}
                onChange={(e) => setGithubRepo(e.target.value)}
                className="bg-slate-900 border-slate-700 text-white mt-2"
                disabled={loading}
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <Label className="text-slate-400 text-xs">Схема в миграциях (заменить)</Label>
                <Input
                  placeholder="t_p90119217_django_layout_develo"
                  value={schemaFrom}
                  onChange={(e) => setSchemaFrom(e.target.value)}
                  className="bg-slate-900 border-slate-700 text-white mt-1 text-sm"
                  disabled={loading}
                />
              </div>
              <div>
                <Label className="text-slate-400 text-xs">На какую схему (в твоей БД)</Label>
                <Input
                  placeholder="public"
                  value={schemaTo}
                  onChange={(e) => setSchemaTo(e.target.value)}
                  className="bg-slate-900 border-slate-700 text-white mt-1 text-sm"
                  disabled={loading}
                />
              </div>
            </div>
            <div>
              <Label className="text-slate-400 text-xs">Замена имён таблиц (JSON)</Label>
              <Input
                placeholder='{"site_content": "editable_content"}'
                value={tableReplaces}
                onChange={(e) => setTableReplaces(e.target.value)}
                className="bg-slate-900 border-slate-700 text-white mt-1 text-sm font-mono"
                disabled={loading}
              />
            </div>
            <Button
              onClick={handleMigrateFromGitHub}
              disabled={!githubRepo.trim() || loading}
              className="w-full bg-gradient-to-r from-green-600 to-emerald-600 hover:from-green-700 hover:to-emerald-700"
              size="lg"
            >
              {loading ? (
                <>
                  <Icon name="Loader2" size={20} className="mr-2 animate-spin" />
                  Применение...
                </>
              ) : (
                <>
                  <Icon name="Database" size={20} className="mr-2" />
                  Применить миграции из GitHub
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white">Загрузка проекта (ZIP)</CardTitle>
            <CardDescription className="text-slate-300">
              Выберите ZIP файл, скачанный из poehali.dev
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-4">
              <label className="flex-1">
                <input
                  type="file"
                  accept=".zip"
                  onChange={handleFileChange}
                  className="hidden"
                  disabled={loading}
                />
                <div className="border-2 border-dashed border-white/30 rounded-lg p-6 cursor-pointer hover:border-white/50 transition-colors text-center">
                  <Icon name="Upload" size={48} className="mx-auto mb-2 text-white/70" />
                  <p className="text-white/70">
                    {file ? file.name : 'Нажмите для выбора файла'}
                  </p>
                </div>
              </label>
            </div>

            <Button
              onClick={handleMigrate}
              disabled={!file || loading}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700"
              size="lg"
            >
              {loading ? (
                <>
                  <Icon name="Loader2" size={20} className="mr-2 animate-spin" />
                  Миграция в процессе...
                </>
              ) : (
                <>
                  <Icon name="Upload" size={20} className="mr-2" />
                  Начать миграцию
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {logs.length > 0 && (
          <Card className="bg-white/10 backdrop-blur border-white/20">
            <CardHeader>
              <CardTitle className="text-white">Логи миграции</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-black/30 rounded-lg p-4 font-mono text-sm space-y-1 max-h-96 overflow-y-auto">
                {logs.map((log, i) => (
                  <div key={i} className="text-green-400 whitespace-pre-wrap">
                    {log}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {result && result.success && (
          <Card className="bg-white/10 backdrop-blur border-white/20">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Icon name="CheckCircle2" size={24} className="text-green-400" />
                Результат миграции
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {result.function_urls && Object.keys(result.function_urls).length > 0 && (
                <div>
                  <h3 className="text-white font-semibold mb-2">Backend функции:</h3>
                  <div className="space-y-2">
                    {Object.entries(result.function_urls).map(([name, url]: [string, any]) => (
                      <div key={name} className="bg-black/30 rounded p-3">
                        <div className="text-purple-300 font-mono text-sm">{name}</div>
                        <div className="text-slate-400 text-xs break-all">{url}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {result.migrations_applied && result.migrations_applied.length > 0 && (
                <div>
                  <h3 className="text-white font-semibold mb-2">Применённые миграции:</h3>
                  <div className="bg-black/30 rounded p-3 space-y-1">
                    {result.migrations_applied.map((migration: string, i: number) => (
                      <div key={i} className="text-green-400 text-sm font-mono">
                        ✓ {migration}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
