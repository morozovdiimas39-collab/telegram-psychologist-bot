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
    github_repo: "",
    vm_ip: "",
    vm_user: "ubuntu"
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
    if (!newConfig.name || !newConfig.domain || !newConfig.github_repo || !newConfig.vm_ip) {
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
          vm_webhook_url: `http://${newConfig.vm_ip}:9000/deploy`
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
        github_repo: "",
        vm_ip: "",
        vm_user: "ubuntu"
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
    setDeployLog([`🚀 Деплой backend функций...`]);

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
        `✅ Backend: ${data.deployed?.length || 0} функций задеплоено`
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

  const handleDeployFrontend = async () => {
    if (!selectedConfig) {
      toast({
        title: "Ошибка",
        description: "Выбери конфигурацию",
        variant: "destructive"
      });
      return;
    }

    setIsDeploying(true);
    setDeployLog([`🚀 Деплой фронтенда для конфига: ${selectedConfig}...`]);

    try {
      const resp = await fetch(API_ENDPOINTS.deploy, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          config_name: selectedConfig
        })
      });

      const data = await resp.json();
      
      if (!resp.ok) {
        throw new Error(data.error || "Ошибка деплоя фронтенда");
      }

      setDeployLog(prev => [
        ...prev,
        "",
        `✅ ${data.message}`,
        "",
        "🎉 Фронтенд деплоится на VM!",
        "⚠️ Убедись что webhook сервер запущен на VM"
      ]);

      toast({
        title: "Деплой фронтенда запущен!",
        description: data.message
      });

    } catch (error: any) {
      setDeployLog(prev => [...prev, "", `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка деплоя фронтенда",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsDeploying(false);
    }
  };

  const handleFullDeploy = async () => {
    const config = configs.find(c => c.name === selectedConfig);
    if (!config) return;

    setIsDeploying(true);
    setDeployLog([`🚀 ПОЛНЫЙ ДЕПЛОЙ: ${selectedConfig}`, ""]);

    try {
      // 1. Backend
      setDeployLog(prev => [...prev, "📦 ШАГ 1/2: Деплой backend функций..."]);
      
      const backendResp = await fetch(API_ENDPOINTS.deployFunctions, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          secrets: [],
          github_repo: config.github_repo
        })
      });

      const backendData = await backendResp.json();
      if (!backendResp.ok) throw new Error(backendData.error || "Ошибка деплоя backend");

      setDeployLog(prev => [
        ...prev,
        ...backendData.logs || [],
        `✅ Backend: ${backendData.deployed?.length || 0} функций`,
        ""
      ]);

      // 2. Frontend
      setDeployLog(prev => [...prev, "🎨 ШАГ 2/2: Деплой фронтенда..."]);
      
      const frontendResp = await fetch(API_ENDPOINTS.deploy, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          config_name: selectedConfig
        })
      });

      const frontendData = await frontendResp.json();
      
      if (frontendResp.ok) {
        setDeployLog(prev => [
          ...prev,
          `✅ ${frontendData.message}`,
          "",
          "🎉 ПОЛНЫЙ ДЕПЛОЙ ЗАВЕРШЁН!",
          `🌐 Сайт: https://${config.domain}`,
          `⚙️ Backend: ${backendData.deployed?.length || 0} функций`
        ]);

        toast({
          title: "🎉 Деплой завершён!",
          description: `Проект доступен на ${config.domain}`
        });
      } else {
        throw new Error(frontendData.error || "Ошибка деплоя фронтенда");
      }

    } catch (error: any) {
      setDeployLog(prev => [...prev, "", `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка деплоя",
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
                  <div className="grid md:grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <div className="text-xs text-slate-400">Домен</div>
                      <div className="text-white font-mono">{currentConfig.domain}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-slate-400">GitHub репозиторий</div>
                      <div className="text-white font-mono text-sm">{currentConfig.github_repo}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-slate-400">IP сервера</div>
                      <div className="text-white font-mono">{currentConfig.vm_ip}</div>
                    </div>
                    <div className="space-y-1">
                      <div className="text-xs text-slate-400">Пользователь</div>
                      <div className="text-white font-mono">{currentConfig.vm_user}</div>
                    </div>
                    <div className="space-y-1 md:col-span-2">
                      <div className="text-xs text-slate-400">Webhook URL</div>
                      <div className="text-white font-mono text-sm">{currentConfig.vm_webhook_url}</div>
                    </div>
                  </div>

                  <div className="bg-blue-500/20 border border-blue-500/50 rounded-lg p-4 space-y-4">
                    <div className="text-blue-300 font-semibold flex items-center gap-2">
                      <Icon name="Rocket" className="h-4 w-4" />
                      Деплой проекта
                    </div>
                    
                    <Button
                      onClick={handleFullDeploy}
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
                          <Icon name="Rocket" className="mr-2 h-5 w-5" />
                          Полный деплой (Backend + Frontend)
                        </>
                      )}
                    </Button>

                    <div className="grid grid-cols-2 gap-2">
                      <Button
                        onClick={handleDeployBackend}
                        disabled={isDeploying}
                        variant="outline"
                        className="border-purple-500/50 hover:bg-purple-500/20 text-purple-300"
                      >
                        <Icon name="Zap" className="mr-2 h-4 w-4" />
                        Backend
                      </Button>
                      <Button
                        onClick={handleDeployFrontend}
                        disabled={isDeploying}
                        variant="outline"
                        className="border-blue-500/50 hover:bg-blue-500/20 text-blue-300"
                      >
                        <Icon name="Globe" className="mr-2 h-4 w-4" />
                        Frontend
                      </Button>
                    </div>

                    <p className="text-slate-400 text-xs">
                      💡 Backend деплоится в Yandex Cloud Functions<br />
                      💡 Frontend отправляется на VM через webhook
                    </p>
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
                Создай конфиг для деплоя на VM
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="config-name">Название <span className="text-red-400">*</span></Label>
                  <Input
                    id="config-name"
                    placeholder="production"
                    value={newConfig.name}
                    onChange={(e) => setNewConfig({...newConfig, name: e.target.value})}
                    className="bg-slate-800 border-slate-700"
                  />
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
                </div>
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
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="config-ip">IP сервера <span className="text-red-400">*</span></Label>
                  <Input
                    id="config-ip"
                    placeholder="158.160.115.239"
                    value={newConfig.vm_ip}
                    onChange={(e) => setNewConfig({...newConfig, vm_ip: e.target.value})}
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="config-user">Пользователь</Label>
                  <Input
                    id="config-user"
                    placeholder="ubuntu"
                    value={newConfig.vm_user}
                    onChange={(e) => setNewConfig({...newConfig, vm_user: e.target.value})}
                    className="bg-slate-800 border-slate-700"
                  />
                </div>
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