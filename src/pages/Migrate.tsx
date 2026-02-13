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
      // GET с query params — не вызывает CORS preflight (OPTIONS)
      const url = `${API_ENDPOINTS.migrate}?github_repo=${encodeURIComponent(githubRepo.trim())}`;
      const response = await fetch(url, { method: 'GET' });

      const data = await response.json();

      if (data.success) {
        setLogs(data.logs || []);
        setResult(data);
        toast.success('Миграции применены!');
      } else {
        setLogs(prev => [...prev, `Ошибка: ${data.error}`]);
        toast.error(data.error || 'Ошибка миграции');
      }
    } catch (error: any) {
      setLogs(prev => [...prev, `Ошибка: ${error.message}`]);
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
            <div>
              <Label className="text-slate-300">Репозиторий GitHub</Label>
              <Input
                placeholder="username/telegram-psychologist-bot-main-2"
                value={githubRepo}
                onChange={(e) => setGithubRepo(e.target.value)}
                className="bg-slate-900 border-slate-700 text-white mt-2"
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