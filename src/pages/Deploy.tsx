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
  const [deployLog, setDeployLog] = useState<string[]>([]);
  const { toast } = useToast();

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
      setDeployLog(prev => [...prev, "", "📦 Шаг 1/3: Деплою backend функции в твой Yandex Cloud..."]);
      const deployResp = await fetch(API_ENDPOINTS.deployFunctions, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ secrets: [] })
      });

      const deployData = await deployResp.json();

      if (!deployResp.ok) {
        throw new Error(deployData.error || "Ошибка деплоя функций");
      }

      setDeployLog(prev => [...prev, ...deployData.logs]);

      if (!deployData.function_urls || Object.keys(deployData.function_urls).length === 0) {
        throw new Error("Не получены URL функций");
      }

      setDeployLog(prev => [...prev, "", "🔄 Шаг 2/3: Обновляю func2url.json в GitHub..."]);
      const updateResp = await fetch(API_ENDPOINTS.updateFunc2url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          function_urls: deployData.function_urls,
          github_repo: githubUrl
        })
      });

      const updateData = await updateResp.json();

      if (!updateResp.ok) {
        throw new Error(updateData.error || "Ошибка обновления func2url.json");
      }

      setDeployLog(prev => [...prev, ...updateData.logs]);

      setDeployLog(prev => [
        ...prev,
        "",
        "✅ Миграция завершена!",
        "",
        "📋 Следующие шаги:",
        "1. Перезапусти фронтенд - он подхватит новые URL из func2url.json",
        "2. Все функции теперь работают в твоём Yandex Cloud с timeout 600 сек!",
        "",
        `✨ Задеплоено функций: ${deployData.deployed?.length || 0}`,
        `✨ Обновлено URL: ${updateData.updated || 0}`
      ]);

      toast({
        title: "🎉 Миграция завершена!",
        description: `${deployData.deployed?.length || 0} функций перенесено в твой Yandex Cloud`
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

        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Icon name="Zap" className="h-6 w-6 text-yellow-400" />
              Автоматическая миграция
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
              disabled={isMigrating || !githubUrl}
              size="lg"
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 hover:from-purple-700 hover:to-blue-700 text-lg h-14"
            >
              {isMigrating ? (
                <>
                  <Icon name="Loader2" className="mr-2 h-5 w-5 animate-spin" />
                  Миграция в процессе...
                </>
              ) : (
                <>
                  <Icon name="Rocket" className="mr-2 h-5 w-5" />
                  Мигрировать на мой Yandex Cloud
                </>
              )}
            </Button>

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

        <Card className="bg-white/5 backdrop-blur border-white/10">
          <CardHeader>
            <CardTitle className="text-white text-sm flex items-center gap-2">
              <Icon name="HelpCircle" className="h-4 w-4" />
              Требования для миграции
            </CardTitle>
          </CardHeader>
          <CardContent className="text-xs text-slate-400 space-y-2">
            <p>✅ <strong>GITHUB_TOKEN</strong> - добавь токен с правами <code className="bg-white/10 px-1 rounded">repo</code> в секреты проекта</p>
            <p>✅ <strong>YANDEX_CLOUD_TOKEN</strong> - OAuth токен для Yandex Cloud (уже добавлен)</p>
            <p>✅ Папка <code className="bg-white/10 px-1 rounded">/backend</code> с функциями в репозитории</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Deploy;
