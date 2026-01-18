import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useToast } from "@/hooks/use-toast";
import Icon from "@/components/ui/icon";
import { API_ENDPOINTS } from "@/lib/api";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";

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

const Deploy = () => {
  const [activeTab, setActiveTab] = useState<'deploy' | 'vms'>('deploy');
  const [vms, setVms] = useState<VMInstance[]>([]);
  const [configs, setConfigs] = useState<DeployConfig[]>([]);
  const [selectedConfig, setSelectedConfig] = useState<string>("");
  const [isLoading, setIsLoading] = useState(true);
  const [isDeploying, setIsDeploying] = useState(false);
  const [isCreatingVM, setIsCreatingVM] = useState(false);
  const [deployLog, setDeployLog] = useState<string[]>([]);
  const [showNewConfigDialog, setShowNewConfigDialog] = useState(false);
  const [showNewVMDialog, setShowNewVMDialog] = useState(false);
  const { toast } = useToast();

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

      setShowNewVMDialog(false);
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

      setShowNewConfigDialog(false);
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

        {/* Tab buttons */}
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

        {/* Deploy tab */}
        {activeTab === 'deploy' && (
          <div className="grid lg:grid-cols-3 gap-6">
            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center justify-between">
                  <span>Конфигурации</span>
                  <Button
                    size="sm"
                    onClick={() => setShowNewConfigDialog(true)}
                    className="bg-green-500 hover:bg-green-600"
                    disabled={vms.length === 0}
                  >
                    <Icon name="Plus" className="h-4 w-4" />
                  </Button>
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {vms.length === 0 ? (
                  <div className="text-center text-slate-400 py-8">
                    <Icon name="Server" className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>Сначала создай VM</p>
                    <p className="text-xs mt-1">Перейди на вкладку "Серверы VM"</p>
                  </div>
                ) : configs.length === 0 ? (
                  <div className="text-center text-slate-400 py-8">
                    <Icon name="FolderOpen" className="h-12 w-12 mx-auto mb-2 opacity-50" />
                    <p>Нет конфигураций</p>
                  </div>
                ) : (
                  configs.map(config => (
                    <div
                      key={config.id}
                      className={`p-3 rounded-lg border cursor-pointer ${
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
                          className="text-red-400"
                        >
                          <Icon name="Trash2" className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))
                )}
              </CardContent>
            </Card>

            <Card className="bg-white/10 backdrop-blur border-white/20 lg:col-span-2">
              <CardHeader>
                <CardTitle className="text-white">
                  {currentConfig ? currentConfig.name : "Выбери конфиг"}
                </CardTitle>
              </CardHeader>
              <CardContent>
                {currentConfig && currentVM ? (
                  <div className="space-y-6">
                    <div className="grid grid-cols-2 gap-4 p-4 bg-slate-900/50 rounded-lg">
                      <div>
                        <div className="text-xs text-slate-400">Домен</div>
                        <div className="text-white">{currentConfig.domain}</div>
                      </div>
                      <div>
                        <div className="text-xs text-slate-400">VM</div>
                        <div className="text-white">{currentVM.name} ({currentVM.ip_address})</div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-3">
                      <Button
                        onClick={() => handleDeploy('all')}
                        disabled={isDeploying}
                        className="bg-purple-600"
                      >
                        Всё
                      </Button>
                      <Button
                        onClick={() => handleDeploy('frontend')}
                        disabled={isDeploying}
                        className="bg-green-600"
                      >
                        Frontend
                      </Button>
                      <Button
                        onClick={() => handleDeploy('backend')}
                        disabled={isDeploying}
                        className="bg-orange-600"
                      >
                        Backend
                      </Button>
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
                    <p>Выбери конфигурацию</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        )}

        {/* VMs tab */}
        {activeTab === 'vms' && (
          <Card className="bg-white/10 backdrop-blur border-white/20">
            <CardHeader>
              <CardTitle className="text-white flex items-center justify-between">
                <span>Серверы VM</span>
                <Button
                  size="sm"
                  onClick={() => setShowNewVMDialog(true)}
                  className="bg-green-500 hover:bg-green-600"
                >
                  <Icon name="Plus" className="mr-2 h-4 w-4" />
                  Создать VM
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {vms.length === 0 ? (
                <div className="text-center text-slate-400 py-12">
                  <Icon name="Server" className="h-16 w-16 mx-auto mb-4 opacity-50" />
                  <p>Нет VM серверов</p>
                </div>
              ) : (
                <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {vms.map(vm => (
                    <div
                      key={vm.id}
                      className="p-4 bg-slate-900/50 border border-slate-700 rounded-lg space-y-3"
                    >
                      <div className="flex items-start justify-between">
                        <div>
                          <div className="text-white font-semibold">{vm.name}</div>
                          <div className="text-xs text-slate-400">{vm.ip_address || 'создаётся...'}</div>
                        </div>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDeleteVM(vm.id)}
                          className="text-red-400"
                        >
                          <Icon name="Trash2" className="h-4 w-4" />
                        </Button>
                      </div>
                      <div className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs ${
                        vm.status === 'ready' ? 'bg-green-500/20 text-green-300' :
                        vm.status === 'creating' ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-red-500/20 text-red-300'
                      }`}>
                        {vm.status}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* Dialog: New VM */}
      {showNewVMDialog && (
        <Dialog open={showNewVMDialog} onOpenChange={setShowNewVMDialog}>
          <DialogContent className="bg-slate-900 border-slate-700 text-white">
            <DialogHeader>
              <DialogTitle>Создать VM</DialogTitle>
              <DialogDescription className="text-slate-400">
                VM создастся в Yandex Cloud (1-2 минуты)
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <Label>Название</Label>
                <Input
                  placeholder="production-server"
                  value={newVM.name}
                  onChange={(e) => setNewVM({ name: e.target.value })}
                  className="bg-slate-800"
                />
              </div>
              <div className="flex gap-3">
                <Button
                  onClick={handleCreateVM}
                  disabled={isCreatingVM}
                  className="flex-1 bg-green-600"
                >
                  {isCreatingVM ? "Создаю..." : "Создать"}
                </Button>
                <Button
                  onClick={() => setShowNewVMDialog(false)}
                  variant="outline"
                  disabled={isCreatingVM}
                >
                  Отмена
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Dialog: New Config */}
      {showNewConfigDialog && (
        <Dialog open={showNewConfigDialog} onOpenChange={setShowNewConfigDialog}>
          <DialogContent className="bg-slate-900 border-slate-700 text-white">
            <DialogHeader>
              <DialogTitle>Новая конфигурация</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 mt-4">
              <div>
                <Label>Название</Label>
                <Input
                  placeholder="production"
                  value={newConfig.name}
                  onChange={(e) => setNewConfig({...newConfig, name: e.target.value})}
                  className="bg-slate-800"
                />
              </div>
              <div>
                <Label>Домен</Label>
                <Input
                  placeholder="mysite.ru"
                  value={newConfig.domain}
                  onChange={(e) => setNewConfig({...newConfig, domain: e.target.value})}
                  className="bg-slate-800"
                />
              </div>
              <div>
                <Label>GitHub репозиторий</Label>
                <Input
                  placeholder="username/repo"
                  value={newConfig.github_repo}
                  onChange={(e) => setNewConfig({...newConfig, github_repo: e.target.value})}
                  className="bg-slate-800"
                />
              </div>
              <div>
                <Label>VM сервер (ID)</Label>
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
              </div>
              <div className="flex gap-3">
                <Button
                  onClick={handleCreateConfig}
                  className="flex-1 bg-green-600"
                >
                  Создать
                </Button>
                <Button
                  onClick={() => setShowNewConfigDialog(false)}
                  variant="outline"
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
