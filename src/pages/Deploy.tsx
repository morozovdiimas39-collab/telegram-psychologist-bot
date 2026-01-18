import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import Icon from "@/components/ui/icon";
import { API_ENDPOINTS } from "@/lib/api";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface DeployConfig {
  id: number;
  name: string;
  domain: string;
  github_repo: string;
  vm_ip: string;
  vm_user: string;
  vm_webhook_url: string;
  created_at: string;
  updated_at: string;
}

const Deploy = () => {
  const [configs, setConfigs] = useState<DeployConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployLog, setDeployLog] = useState<string[]>([]);
  const [showNewConfigDialog, setShowNewConfigDialog] = useState(false);
  const { toast } = useToast();

  const [newConfig, setNewConfig] = useState({
    name: "",
    domain: "",
    github_repo: ""
  });

  useEffect(() => {
    loadConfigs();
  }, []);

  const loadConfigs = async () => {
    try {
      const resp = await fetch(API_ENDPOINTS.deployConfig);
      const data = await resp.json();
      setConfigs(data);
      if (data.length > 0 && !selectedConfig) {
        setSelectedConfig(data[0].name);
      }
    } catch (error: any) {
      toast({
        title: "Ошибка загрузки конфигов",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateConfig = async () => {
    if (!newConfig.name || !newConfig.domain || !newConfig.github_repo) {
      toast({
        title: "Ошибка",
        description: "Заполни все обязательные поля",
        variant: "destructive"
      });
      return;
    }

    try {
      const resp = await fetch(API_ENDPOINTS.deployConfig, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...newConfig,
          vm_ip: "0.0.0.0",
          vm_user: "ubuntu"
        })
      });

      if (!resp.ok) {
        const error = await resp.json();
        throw new Error(error.error || "Ошибка создания конфига");
      }

      toast({
        title: "Конфиг создан!",
        description: `Конфиг ${newConfig.name} успешно создан`
      });

      setShowNewConfigDialog(false);
      setNewConfig({
        name: "",
        domain: "",
        github_repo: ""
      });
      loadConfigs();
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    }
  };

  const handleDeployBackend = async () => {
    const config = configs.find(c => c.name === selectedConfig);
    if (!config) return;

    setIsDeploying(true);
    setDeployLog([`🚀 Деплой backend функций из ${config.github_repo}...`, ""]);

    try {
      const resp = await fetch(API_ENDPOINTS.deployFunctions, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          secrets: [],
          github_repo: config.github_repo
        })
      });

      const data = await resp.json();
      
      if (!resp.ok) {
        throw new Error(data.error || "Ошибка деплоя backend");
      }

      setDeployLog(prev => [
        ...prev,
        ...data.logs || [],
        "",
        "🎉 ДЕПЛОЙ ЗАВЕРШЁН!",
        `✅ Задеплоено: ${data.deployed?.length || 0} функций`,
        `⚙️ Yandex Cloud Functions активны`,
        "",
        "📝 func2url.json обновлён в репозитории"
      ]);

      toast({
        title: "Backend задеплоен!",
        description: `${data.deployed?.length || 0} функций в Yandex Cloud`
      });

    } catch (error: any) {
      setDeployLog(prev => [...prev, "", `❌ Ошибка backend: ${error.message}`]);
      toast({
        title: "Ошибка деплоя backend",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsDeploying(false);
    }
  };

  const handleDeleteConfig = async (name: string) => {
    if (!confirm(`Удалить конфиг "${name}"?`)) return;

    try {
      const resp = await fetch(`${API_ENDPOINTS.deployConfig}?name=${name}`, {
        method: "DELETE"
      });

      if (!resp.ok) {
        const error = await resp.json();
        throw new Error(error.error || "Ошибка удаления");
      }

      toast({
        title: "Конфиг удалён",
        description: `Конфиг ${name} успешно удалён`
      });

      loadConfigs();
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center">
        <div className="text-white text-xl">Загрузка...</div>
      </div>
    );
  }

  const currentConfig = configs.find(c => c.name === selectedConfig);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-6xl py-8 space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-white">Деплой проекта</h1>
          <p className="text-slate-300 text-lg">
            Управление конфигурациями и деплой на VM
          </p>
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Список конфигов */}
          <Card className="bg-white/10 backdrop-blur border-white/20">
            <CardHeader>
              <CardTitle className="text-white flex items-center justify-between">
                <span className="flex items-center gap-2">
                  <Icon name="Settings" className="h-5 w-5" />
                  Конфигурации
                </span>
                <Button
                  size="sm"
                  onClick={() => setShowNewConfigDialog(true)}
                  className="bg-green-500 hover:bg-green-600"
                >
                  <Icon name="Plus" className="h-4 w-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {configs.length === 0 ? (
                <div className="text-center text-slate-400 py-8">
                  <Icon name="FolderOpen" className="h-12 w-12 mx-auto mb-2 opacity-50" />
                  <p>Нет конфигураций</p>
                  <p className="text-xs mt-1">Создай первую!</p>
                </div>
              ) : (
                configs.map(config => (
                  <div
                    key={config.id}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedConfig === config.name
                        ? 'bg-blue-500/30 border-blue-400'
                        : 'bg-white/5 border-white/10 hover:bg-white/10'
                    }`}
                    onClick={() => setSelectedConfig(config.name)}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="text-white font-semibold">{config.name}</div>
                        <div className="text-xs text-slate-400">{config.domain}</div>
                      </div>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={(e) => {
                          e.stopPropagation();
                          handleDeleteConfig(config.name);
                        }}
                        className="text-red-400 hover:text-red-300 hover:bg-red-500/20"
                      >
                        <Icon name="Trash2" className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>

          {/* Детали конфига */}
          <Card className="bg-white/10 backdrop-blur border-white/20 lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-white flex items-center gap-2">
                <Icon name="Info" className="h-5 w-5" />
                {currentConfig ? currentConfig.name : "Выбери конфиг"}
              </CardTitle>
              <CardDescription className="text-slate-300">
                Информация о конфигурации деплоя
              </CardDescription>
            </CardHeader>
            <CardContent>
              {currentConfig ? (
                <div className="space-y-6">
                  <div className="space-y-3">
                    <div className="space-y-1">
                      <div className="text-xs text-slate-400">Домен проекта</div>
                      <div className="text-white font-mono text-lg">{currentConfig.domain}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-slate-400">GitHub репозиторий</div>
                      <a 
                        href={`https://github.com/${currentConfig.github_repo}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:text-blue-300 font-mono text-sm flex items-center gap-1"
                      >
                        {currentConfig.github_repo}
                        <Icon name="ExternalLink" className="h-3 w-3" />
                      </a>
                    </div>
                  </div>

                  <div className="bg-blue-500/20 border border-blue-500/50 rounded-lg p-4 space-y-4">
                    <div className="text-blue-300 font-semibold flex items-center gap-2">
                      <Icon name="Zap" className="h-4 w-4" />
                      Деплой Backend функций
                    </div>
                    
                    <p className="text-slate-300 text-sm">
                      Задеплой все backend функции из репозитория <span className="font-mono text-blue-300">{currentConfig.github_repo}</span> в Yandex Cloud Functions.
                    </p>

                    <Button
                      onClick={handleDeployBackend}
                      disabled={isDeploying}
                      className="w-full bg-gradient-to-r from-purple-500 to-blue-500 hover:from-purple-600 hover:to-blue-600 text-white font-bold"
                    >
                      {isDeploying ? (
                        <>
                          <Icon name="Loader2" className="mr-2 h-5 w-5 animate-spin" />
                          Деплой...
                        </>
                      ) : (
                        <>
                          <Icon name="Zap" className="mr-2 h-5 w-5" />
                          Задеплоить Backend
                        </>
                      )}
                    </Button>

                    <div className="bg-slate-900/50 rounded-lg p-3 space-y-2">
                      <div className="text-xs text-slate-400 font-semibold">Что деплоится:</div>
                      <div className="space-y-1 text-xs text-slate-300">
                        <div className="flex items-center gap-2">
                          <Icon name="Check" className="h-3 w-3 text-green-400" />
                          Все функции из <span className="font-mono">/backend/</span>
                        </div>
                        <div className="flex items-center gap-2">
                          <Icon name="Check" className="h-3 w-3 text-green-400" />
                          Развёртывание в Yandex Cloud Functions
                        </div>
                        <div className="flex items-center gap-2">
                          <Icon name="Check" className="h-3 w-3 text-green-400" />
                          Автообновление <span className="font-mono">func2url.json</span>
                        </div>
                      </div>
                    </div>

                    <div className="bg-yellow-500/10 border border-yellow-500/50 rounded-lg p-3">
                      <div className="text-yellow-300 text-xs font-semibold mb-1 flex items-center gap-1">
                        <Icon name="Info" className="h-3 w-3" />
                        Frontend деплой
                      </div>
                      <p className="text-yellow-200 text-xs">
                        Frontend (сайт) деплоится через GitHub → Vercel/Netlify автоматически при пуше в main ветку.
                      </p>
                    </div>
                  </div>

                  {deployLog.length > 0 && (
                    <div className="bg-slate-900/50 border border-slate-700 rounded-lg p-4 font-mono text-sm text-slate-300 max-h-96 overflow-y-auto">
                      {deployLog.map((log, i) => (
                        <div key={i}>{log}</div>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center text-slate-400 py-12">
                  <Icon name="MousePointerClick" className="h-16 w-16 mx-auto mb-4 opacity-50" />
                  <p>Выбери конфигурацию слева</p>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Диалог создания конфига */}
      {showNewConfigDialog && (
        <Dialog open={showNewConfigDialog} onOpenChange={setShowNewConfigDialog}>
          <DialogContent className="bg-slate-900 border-slate-700 text-white max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Новая конфигурация</DialogTitle>
              <DialogDescription className="text-slate-400">
                Создай конфиг для деплоя backend функций
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label htmlFor="config-name">Название <span className="text-red-400">*</span></Label>
                <Input
                  id="config-name"
                  placeholder="production"
                  value={newConfig.name}
                  onChange={(e) => setNewConfig({...newConfig, name: e.target.value})}
                  className="bg-slate-800 border-slate-700"
                />
                <p className="text-xs text-slate-500">production, staging, development</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="config-domain">Домен <span className="text-red-400">*</span></Label>
                <Input
                  id="config-domain"
                  placeholder="mysite.ru"
                  value={newConfig.domain}
                  onChange={(e) => setNewConfig({...newConfig, domain: e.target.value})}
                  className="bg-slate-800 border-slate-700"
                />
                <p className="text-xs text-slate-500">Домен где будет доступен сайт</p>
              </div>

              <div className="space-y-2">
                <Label htmlFor="config-repo">GitHub репозиторий <span className="text-red-400">*</span></Label>
                <Input
                  id="config-repo"
                  placeholder="username/repo-name"
                  value={newConfig.github_repo}
                  onChange={(e) => setNewConfig({...newConfig, github_repo: e.target.value})}
                  className="bg-slate-800 border-slate-700"
                />
                <p className="text-xs text-slate-500">Репозиторий с backend функциями</p>
              </div>



              <div className="flex gap-3 pt-4">
                <Button
                  onClick={handleCreateConfig}
                  className="flex-1 bg-green-600 hover:bg-green-700"
                >
                  <Icon name="Check" className="mr-2 h-4 w-4" />
                  Создать конфиг
                </Button>
                <Button
                  onClick={() => setShowNewConfigDialog(false)}
                  variant="outline"
                  className="border-slate-700 hover:bg-slate-800"
                >
                  Отмена
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default Deploy;