import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import Icon from "@/components/ui/icon";
import { API_ENDPOINTS } from "@/lib/api";

const Deploy = () => {
  const [githubUrl, setGithubUrl] = useState("");
  const [isMigrating, setIsMigrating] = useState(false);
  const [isBootstrapping, setIsBootstrapping] = useState(false);
  const [deployLog, setDeployLog] = useState<string[]>([]);
  const [bootstrapComplete, setBootstrapComplete] = useState(false);
  const { toast } = useToast();

  const handleBootstrapDeployFunction = async () => {
    if (!githubUrl) {
      toast({
        title: "Ошибка",
        description: "Укажи GitHub репозиторий",
        variant: "destructive"
      });
      return;
    }

    setIsBootstrapping(true);
    setDeployLog(["🔧 Переношу deploy-functions в твой Yandex Cloud..."]);

    try {
      const deployResp = await fetch(API_ENDPOINTS.deployFunctions, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          secrets: [],
          github_repo: githubUrl,
          offset: 0,
          batch_size: 1,
          function_filter: "deploy-functions"
        })
      });

      const deployData = await deployResp.json();

      if (!deployResp.ok) {
        throw new Error(deployData.error || "Ошибка деплоя");
      }

      setDeployLog(prev => [...prev, ...deployData.logs]);

      if (deployData.deployed && deployData.deployed.length > 0) {
        setDeployLog(prev => [
          ...prev,
          "",
          "✅ deploy-functions перенесена в твой Yandex Cloud!",
          "✅ Timeout увеличен до 600 сек",
          "",
          "👉 Теперь можешь мигрировать остальные функции"
        ]);
        setBootstrapComplete(true);
        toast({
          title: "🎉 Готово!",
          description: "Теперь можно мигрировать все функции"
        });
      } else {
        throw new Error("Функция не задеплоилась");
      }

    } catch (error: any) {
      setDeployLog(prev => [...prev, "", `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsBootstrapping(false);
    }
  };

  const handleMigrateToYandexCloud = async () => {
    if (!githubUrl) {
      toast({
        title: "Ошибка",
        description: "Укажи GitHub репозиторий (например: username/repo)",
        variant: "destructive"
      });
      return;
    }

    setIsMigrating(true);
    setDeployLog(["🚀 Начинаю полную миграцию на Yandex Cloud..."]);

    try {
      let offset = 0;
      let hasMore = true;
      let totalDeployed = 0;

      while (hasMore) {
        setDeployLog(prev => [...prev, "", `📦 Деплою пачку функций (offset: ${offset})...`]);
        
        const deployResp = await fetch(API_ENDPOINTS.deployFunctions, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ 
            secrets: [],
            github_repo: githubUrl,
            offset: offset,
            batch_size: 5
          })
        });

        const deployData = await deployResp.json();

        if (!deployResp.ok) {
          throw new Error(deployData.error || "Ошибка деплоя функций");
        }

        setDeployLog(prev => [...prev, ...deployData.logs]);
        
        totalDeployed = deployData.deployed_count || (totalDeployed + deployData.deployed?.length || 0);
        hasMore = deployData.has_more || false;
        
        if (hasMore) {
          offset = deployData.next_offset || (offset + 5);
          setDeployLog(prev => [...prev, "", `⏳ Пауза 2 сек перед следующей пачкой...`]);
          await new Promise(resolve => setTimeout(resolve, 2000));
        }
      }

      setDeployLog(prev => [
        ...prev,
        "",
        "✅ Миграция завершена!",
        "",
        "📋 Следующие шаги:",
        "1. Перезапусти фронтенд - он подхватит новые URL из func2url.json",
        "2. Все функции теперь работают в твоём Yandex Cloud с timeout 600 сек!",
        "",
        `✨ Всего задеплоено функций: ${totalDeployed}`
      ]);

      toast({
        title: "🎉 Миграция завершена!",
        description: `${totalDeployed} функций перенесено в твой Yandex Cloud`
      });

    } catch (error: any) {
      setDeployLog(prev => [...prev, "", `❌ Ошибка миграции: ${error.message}`]);
      toast({
        title: "Ошибка миграции",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsMigrating(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-4xl py-8 space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-white">Миграция на Yandex Cloud</h1>
          <p className="text-slate-300 text-lg">
            Перенеси все backend функции в свой облачный аккаунт за один клик
          </p>
        </div>

        <Card className="bg-red-500/10 backdrop-blur border-red-500/30">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2 text-base">
              <Icon name="AlertCircle" className="h-5 w-5 text-red-400" />
              ШАГ 1: Перенос deploy-functions (обязательно!)
            </CardTitle>
            <CardDescription className="text-slate-300 text-sm">
              Сначала нужно перенести саму функцию деплоя в твой Yandex Cloud, иначе она упадёт по таймауту 30 сек
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="github-repo-bootstrap" className="text-white text-sm">
                GitHub репозиторий <span className="text-red-400">*</span>
              </Label>
              <Input
                id="github-repo-bootstrap"
                placeholder="username/repository"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                disabled={isBootstrapping || bootstrapComplete}
                className="bg-white/10 border-white/20 text-white placeholder:text-slate-400"
              />
            </div>

            <Button
              onClick={handleBootstrapDeployFunction}
              disabled={isBootstrapping || !githubUrl || bootstrapComplete}
              size="lg"
              className="w-full bg-red-600 hover:bg-red-700 text-base h-12"
            >
              {isBootstrapping ? (
                <>
                  <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                  Переношу deploy-functions...
                </>
              ) : bootstrapComplete ? (
                <>
                  <Icon name="CheckCircle2" className="mr-2 h-4 w-4" />
                  Готово! Переходи к Шагу 2
                </>
              ) : (
                <>
                  <Icon name="Upload" className="mr-2 h-4 w-4" />
                  Перенести deploy-functions
                </>
              )}
            </Button>

            <p className="text-xs text-slate-400">
              ⚠️ Без этого шага миграция всех функций упадёт по таймауту на poehali.dev (30 сек)
            </p>
          </CardContent>
        </Card>

        <Card className={`bg-white/10 backdrop-blur border-white/20 ${!bootstrapComplete ? 'opacity-50' : ''}`}>
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Icon name="Zap" className="h-6 w-6 text-yellow-400" />
              ШАГ 2: Миграция всех функций
            </CardTitle>
            <CardDescription className="text-slate-300">
              Получи полный контроль над функциями: timeout 600 сек вместо 30, неограниченные вызовы
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="bg-green-500/20 border border-green-500/50 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-green-300 font-semibold">
                <Icon name="CheckCircle2" className="h-5 w-5" />
                Что даёт миграция?
              </div>
              <ul className="text-sm text-slate-300 space-y-1 ml-7">
                <li>⏱ <strong>Timeout 600 сек</strong> (вместо 30!) - генерация документов на 100+ страниц</li>
                <li>🚀 <strong>Неограниченные вызовы</strong> (не 50k/месяц) - любая нагрузка</li>
                <li>💾 <strong>256MB памяти</strong> (можно до 4GB) - обработка больших файлов</li>
                <li>💰 <strong>Оплата по факту</strong> в твоём Yandex Cloud</li>
              </ul>
            </div>

            <div className="space-y-2">
              <Label htmlFor="github-repo" className="text-white">
                GitHub репозиторий <span className="text-red-400">*</span>
              </Label>
              <Input
                id="github-repo"
                placeholder="username/repository (например: ivanov/my-project)"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                disabled={isMigrating}
                className="bg-white/10 border-white/20 text-white placeholder:text-slate-400"
              />
              <p className="text-xs text-slate-400">
                Формат: <code className="bg-white/10 px-1 rounded">username/repo-name</code>
              </p>
            </div>

            <Button
              onClick={handleMigrateToYandexCloud}
              disabled={isMigrating || !githubUrl || !bootstrapComplete}
              size="lg"
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-lg h-14"
            >
              {isMigrating ? (
                <>
                  <Icon name="Loader2" className="mr-2 h-5 w-5 animate-spin" />
                  Миграция в процессе...
                </>
              ) : !bootstrapComplete ? (
                <>
                  <Icon name="Lock" className="mr-2 h-5 w-5" />
                  Сначала выполни Шаг 1
                </>
              ) : (
                <>
                  <Icon name="Rocket" className="mr-2 h-5 w-5" />
                  Мигрировать все функции
                </>
              )}
            </Button>

            {!bootstrapComplete && (
              <p className="text-xs text-yellow-300 text-center">
                ⚠️ Кнопка разблокируется после Шага 1
              </p>
            )}

            <div className="bg-blue-500/20 border border-blue-500/50 rounded-lg p-4 space-y-2">
              <div className="flex items-center gap-2 text-blue-300 font-semibold text-sm">
                <Icon name="Info" className="h-4 w-4" />
                Что происходит при нажатии?
              </div>
              <ol className="text-xs text-slate-300 space-y-1 ml-7 list-decimal">
                <li>Деплоятся все функции из <code className="bg-white/10 px-1 rounded">/backend</code> в твой Yandex Cloud</li>
                <li>Обновляется <code className="bg-white/10 px-1 rounded">func2url.json</code> с новыми URL</li>
                <li>Автоматический коммит изменений в GitHub</li>
                <li>Готово! Перезапусти фронтенд - всё работает с твоими функциями</li>
              </ol>
            </div>
          </CardContent>
        </Card>

        {deployLog.length > 0 && (
          <Card className="bg-white/10 backdrop-blur border-white/20">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Icon name="Terminal" className="h-5 w-5" />
                Логи миграции
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="bg-black/50 rounded-lg p-4 font-mono text-sm space-y-1 max-h-96 overflow-y-auto">
                {deployLog.map((log, i) => (
                  <div 
                    key={i} 
                    className={`${
                      log.startsWith('✅') ? 'text-green-400' :
                      log.startsWith('❌') ? 'text-red-400' :
                      log.startsWith('🚀') || log.startsWith('📦') || log.startsWith('🔄') ? 'text-blue-400 font-semibold' :
                      'text-slate-300'
                    }`}
                  >
                    {log}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        <Card className="bg-yellow-500/10 backdrop-blur border-yellow-500/30">
          <CardHeader>
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Icon name="Key" className="h-4 w-4 text-yellow-400" />
              Требуется: GITHUB_TOKEN
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm text-slate-300 space-y-2">
              <p>Для автоматического обновления <code className="bg-white/10 px-1 rounded">func2url.json</code> нужен GitHub токен:</p>
              <ol className="list-decimal list-inside space-y-1 text-xs ml-2">
                <li>Открой <a href="https://github.com/settings/tokens/new" target="_blank" className="text-blue-400 hover:underline">github.com/settings/tokens/new</a></li>
                <li>Название: <code className="bg-white/10 px-1 rounded">poehali-deploy</code></li>
                <li>Права: отметь весь раздел <strong>repo</strong></li>
                <li>Создай токен и скопируй его</li>
                <li>Добавь секрет <code className="bg-white/10 px-1 rounded">GITHUB_TOKEN</code> в проект через меню "Секреты"</li>
              </ol>
              <p className="text-xs text-yellow-300">
                ⚠️ Без этого токена func2url.json не обновится автоматически
              </p>
            </div>
            
            <div className="flex gap-2">
              <Button
                onClick={() => window.open('https://github.com/settings/tokens/new', '_blank')}
                variant="outline"
                size="sm"
                className="bg-white/10 border-white/20 text-white hover:bg-white/20"
              >
                <Icon name="ExternalLink" className="mr-2 h-3 w-3" />
                Создать токен GitHub
              </Button>
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-white/5 backdrop-blur border-white/10">
          <CardHeader>
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Icon name="CheckCircle2" className="h-4 w-4" />
              Также требуется
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-slate-400 space-y-2">
            <p>✅ <strong>YANDEX_CLOUD_TOKEN</strong> - OAuth токен для Yandex Cloud (уже добавлен)</p>
            <p>✅ Папка <code className="bg-white/10 px-1 rounded">/backend</code> с функциями в GitHub репозитории</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Deploy;