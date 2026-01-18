import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import Icon from "@/components/ui/icon";
import { API_ENDPOINTS } from "@/lib/api";

interface VMInstance {
  id: number;
  name: string;
  ip_address: string | null;
  ssh_user: string;
  status: string;
  yandex_vm_id: string | null;
  created_at: string;
  updated_at: string;
}

interface DeployConfig {
  id: number;
  name: string;
  domain: string;
  github_repo: string;
  vm_instance_id: number | null;
  created_at: string;
  updated_at: string;
}

export default function Deploy() {
  const { toast } = useToast();
  const [activeTab, setActiveTab] = useState<'deploy' | 'vms'>('deploy');
  const [vms, setVms] = useState<VMInstance[]>([]);
  const [configs, setConfigs] = useState<DeployConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isDeploying, setIsDeploying] = useState(false);
  const [isCreatingVM, setIsCreatingVM] = useState(false);
  const [deployLog, setDeployLog] = useState<string[]>([]);

  const [newConfig, setNewConfig] = useState({
    name: "",
    domain: "",
    github_repo: "",
    vm_instance_id: ""
  });

  const [newVM, setNewVM] = useState({
    name: ""
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      await Promise.all([loadVMs(), loadConfigs()]);
    } finally {
      setIsLoading(false);
    }
  };

  const loadVMs = async () => {
    try {
      const resp = await fetch(API_ENDPOINTS.vmList);
      const data = await resp.json();
      setVms(data);
    } catch (error: any) {
      toast({
        title: "Ошибка загрузки VM",
        description: error.message,
        variant: "destructive"
      });
    }
  };

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
    }
  };

  const handleCreateVM = async () => {
    if (!newVM.name) {
      toast({
        title: "Ошибка",
        description: "Укажи название VM",
        variant: "destructive"
      });
      return;
    }

    setIsCreatingVM(true);
    try {
      const resp = await fetch(API_ENDPOINTS.vmCreate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(newVM)
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка создания VM");
      }

      toast({
        title: data.status === 'ready' ? "VM создана!" : "VM создаётся",
        description: data.status === 'ready' 
          ? `VM ${newVM.name} готова: ${data.ip_address}` 
          : "Создание займёт 1-2 минуты. Обнови список VM."
      });

      setNewVM({ name: "" });
      loadVMs();
    } catch (error: any) {
      toast({
        title: "Ошибка создания VM",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsCreatingVM(false);
    }
  };

  const handleCreateConfig = async () => {
    if (!newConfig.name || !newConfig.domain || !newConfig.github_repo || !newConfig.vm_instance_id) {
      toast({
        title: "Ошибка",
        description: "Заполни все поля",
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
          vm_instance_id: parseInt(newConfig.vm_instance_id)
        })
      });

      if (!resp.ok) {
        const error = await resp.json();
        throw new Error(error.error || "Ошибка создания конфига");
      }

      toast({
        title: "Конфиг создан!",
        description: `Конфиг ${newConfig.name} создан`
      });

      setNewConfig({ name: "", domain: "", github_repo: "", vm_instance_id: "" });
      loadConfigs();
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    }
  };

  const handleDeploy = async (type: 'all' | 'frontend' | 'backend') => {
    const config = configs.find(c => c.name === selectedConfig);
    if (!config) return;

    setIsDeploying(true);
    setDeployLog([`🚀 Запуск деплоя: ${type === 'all' ? 'всё' : type}...`, ""]);

    try {
      const resp = await fetch(API_ENDPOINTS.deploy, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          config_name: selectedConfig,
          type: type
        })
      });

      const data = await resp.json();
      
      if (!resp.ok) {
        throw new Error(data.error || "Ошибка деплоя");
      }

      setDeployLog(prev => [
        ...prev,
        ...data.logs || []
      ]);

      toast({
        title: "Информация получена",
        description: "Проверь логи деплоя"
      });

    } catch (error: any) {
      setDeployLog(prev => [...prev, "", `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка",
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
        title: "Конфиг удалён"
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

  const handleDeleteVM = async (id: number) => {
    if (!confirm("Удалить VM из списка?")) return;

    try {
      const resp = await fetch(`${API_ENDPOINTS.vmList}?id=${id}`, {
        method: "DELETE"
      });

      if (!resp.ok) {
        const error = await resp.json();
        throw new Error(error.error || "Ошибка удаления");
      }

      toast({
        title: "VM удалена"
      });

      loadVMs();
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
  const currentVM = currentConfig && vms.find(v => v.id === currentConfig.vm_instance_id);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-7xl py-8 space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-white">Деплой проектов</h1>
          <p className="text-slate-300 text-lg">
            Управление VM и деплой проектов
          </p>
        </div>

        <div className="flex gap-4 justify-center">
          <Button
            onClick={() => setActiveTab('deploy')}
            variant={activeTab === 'deploy' ? 'default' : 'outline'}
            className={activeTab === 'deploy' ? 'bg-blue-600' : ''}
          >
            <Icon name="Rocket" className="mr-2 h-4 w-4" />
            Деплой
          </Button>
          <Button
            onClick={() => setActiveTab('vms')}
            variant={activeTab === 'vms' ? 'default' : 'outline'}
            className={activeTab === 'vms' ? 'bg-blue-600' : ''}
          >
            <Icon name="Server" className="mr-2 h-4 w-4" />
            Серверы VM
          </Button>
        </div>

        {activeTab === 'deploy' && (
          <div className="grid lg:grid-cols-3 gap-6">
            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center justify-between">
                  <span>Конфигурации</span>
                </CardTitle>
                <CardDescription className="text-slate-300">
                  Выбери конфиг для деплоя
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label className="text-white">Конфиг проекта</Label>
                  <select
                    value={selectedConfig}
                    onChange={(e) => setSelectedConfig(e.target.value)}
                    className="w-full p-2 rounded bg-slate-800 text-white border border-slate-700"
                  >
                    <option value="">Выбери конфиг</option>
                    {configs.map(config => (
                      <option key={config.id} value={config.name}>
                        {config.name}
                      </option>
                    ))}
                  </select>
                </div>

                {currentConfig && (
                  <div className="space-y-3 pt-4 border-t border-white/10">
                    <div>
                      <div className="text-xs text-slate-400">Домен</div>
                      <div className="text-white font-mono text-sm">{currentConfig.domain}</div>
                    </div>
                    <div>
                      <div className="text-xs text-slate-400">Репозиторий</div>
                      <div className="text-white font-mono text-sm">{currentConfig.github_repo}</div>
                    </div>
                    {currentVM && (
                      <div>
                        <div className="text-xs text-slate-400">VM сервер</div>
                        <div className="text-white text-sm">
                          {currentVM.name} ({currentVM.ip_address || 'IP не назначен'})
                        </div>
                        <div className="text-xs text-slate-400 mt-1">
                          Статус: <span className={currentVM.status === 'ready' ? 'text-green-400' : 'text-yellow-400'}>
                            {currentVM.status}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                <div className="pt-4 space-y-2">
                  <div className="text-sm font-medium text-white mb-2">Добавить новый конфиг</div>
                  <Input
                    placeholder="Название (production)"
                    value={newConfig.name}
                    onChange={(e) => setNewConfig({...newConfig, name: e.target.value})}
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                  <Input
                    placeholder="Домен (example.com)"
                    value={newConfig.domain}
                    onChange={(e) => setNewConfig({...newConfig, domain: e.target.value})}
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                  <Input
                    placeholder="GitHub (user/repo)"
                    value={newConfig.github_repo}
                    onChange={(e) => setNewConfig({...newConfig, github_repo: e.target.value})}
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                  <select
                    value={newConfig.vm_instance_id}
                    onChange={(e) => setNewConfig({...newConfig, vm_instance_id: e.target.value})}
                    className="w-full p-2 rounded bg-slate-800 text-white border border-slate-700"
                  >
                    <option value="">Выбери VM</option>
                    {vms.filter(vm => vm.status === 'ready').map(vm => (
                      <option key={vm.id} value={vm.id}>
                        {vm.name} ({vm.ip_address})
                      </option>
                    ))}
                  </select>
                  <Button 
                    onClick={handleCreateConfig}
                    className="w-full bg-green-600 hover:bg-green-700"
                  >
                    <Icon name="Plus" className="mr-2 h-4 w-4" />
                    Создать конфиг
                  </Button>
                </div>

                {configs.length > 0 && (
                  <div className="pt-4 border-t border-white/10">
                    <div className="text-sm font-medium text-white mb-2">Все конфиги</div>
                    <div className="space-y-2">
                      {configs.map(config => (
                        <div key={config.id} className="flex justify-between items-center text-sm">
                          <span className="text-white">{config.name}</span>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeleteConfig(config.name)}
                            className="text-red-400 hover:text-red-300"
                          >
                            <Icon name="Trash2" className="h-4 w-4" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white">Действия деплоя</CardTitle>
                <CardDescription className="text-slate-300">
                  Что хочешь задеплоить?
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button
                  onClick={() => handleDeploy('all')}
                  disabled={!selectedConfig || isDeploying}
                  className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                >
                  <Icon name="Zap" className="mr-2 h-4 w-4" />
                  Деплой: Всё
                </Button>

                <Button
                  onClick={() => handleDeploy('frontend')}
                  disabled={!selectedConfig || isDeploying}
                  variant="outline"
                  className="w-full border-blue-500 text-blue-400 hover:bg-blue-500/20"
                >
                  <Icon name="Globe" className="mr-2 h-4 w-4" />
                  Деплой: Frontend
                </Button>

                <Button
                  onClick={() => handleDeploy('backend')}
                  disabled={!selectedConfig || isDeploying}
                  variant="outline"
                  className="w-full border-purple-500 text-purple-400 hover:bg-purple-500/20"
                >
                  <Icon name="Server" className="mr-2 h-4 w-4" />
                  Деплой: Backend
                </Button>

                {isDeploying && (
                  <div className="text-center text-blue-400 text-sm animate-pulse">
                    Выполняется деплой...
                  </div>
                )}
              </CardContent>
            </Card>

            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white">Лог деплоя</CardTitle>
                <CardDescription className="text-slate-300">
                  Информация о процессе
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-950/50 rounded-lg p-4 font-mono text-xs text-slate-300 max-h-96 overflow-y-auto">
                  {deployLog.length === 0 ? (
                    <div className="text-slate-500">Лог пуст. Запусти деплой.</div>
                  ) : (
                    deployLog.map((line, i) => (
                      <div key={i} className="mb-1">{line}</div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {activeTab === 'vms' && (
          <div className="grid lg:grid-cols-2 gap-6">
            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white">Создать новую VM</CardTitle>
                <CardDescription className="text-slate-300">
                  Новый сервер в Yandex Cloud
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label className="text-white">Название VM</Label>
                  <Input
                    placeholder="prod-server-1"
                    value={newVM.name}
                    onChange={(e) => setNewVM({name: e.target.value})}
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                </div>
                <Button
                  onClick={handleCreateVM}
                  disabled={isCreatingVM}
                  className="w-full bg-blue-600 hover:bg-blue-700"
                >
                  {isCreatingVM ? (
                    <>Создаю VM...</>
                  ) : (
                    <>
                      <Icon name="Plus" className="mr-2 h-4 w-4" />
                      Создать VM
                    </>
                  )}
                </Button>
                <div className="text-xs text-slate-400 border-t border-white/10 pt-4">
                  <div className="font-semibold mb-2">Что будет установлено:</div>
                  <ul className="space-y-1">
                    <li>• Nginx для хостинга</li>
                    <li>• Certbot для SSL</li>
                    <li>• Bun для запуска приложений</li>
                    <li>• SSH ключ для деплоя</li>
                  </ul>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white">Список VM</CardTitle>
                <CardDescription className="text-slate-300">
                  Все серверы проекта
                </CardDescription>
              </CardHeader>
              <CardContent>
                {vms.length === 0 ? (
                  <div className="text-slate-400 text-center py-8">
                    Нет VM серверов. Создай первый!
                  </div>
                ) : (
                  <div className="space-y-4">
                    {vms.map(vm => (
                      <div key={vm.id} className="bg-slate-900/50 rounded-lg p-4 border border-white/10">
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <div className="font-semibold text-white">{vm.name}</div>
                            <div className="text-xs text-slate-400">ID: {vm.id}</div>
                          </div>
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleDeleteVM(vm.id)}
                            className="text-red-400 hover:text-red-300"
                          >
                            <Icon name="Trash2" className="h-4 w-4" />
                          </Button>
                        </div>
                        <div className="space-y-1 text-sm">
                          <div className="flex justify-between">
                            <span className="text-slate-400">IP:</span>
                            <span className="text-white font-mono">
                              {vm.ip_address || 'Не назначен'}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Статус:</span>
                            <span className={
                              vm.status === 'ready' ? 'text-green-400' : 
                              vm.status === 'creating' ? 'text-yellow-400' : 
                              'text-red-400'
                            }>
                              {vm.status}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Пользователь:</span>
                            <span className="text-white font-mono">{vm.ssh_user}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-slate-400">Создана:</span>
                            <span className="text-white text-xs">
                              {new Date(vm.created_at).toLocaleString('ru-RU')}
                            </span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
