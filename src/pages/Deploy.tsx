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
  vm_ip?: string;
  created_at: string;
  updated_at: string;
}

export default function Deploy() {
  const { toast } = useToast();
  const [vms, setVms] = useState<VMInstance[]>([]);
  const [configs, setConfigs] = useState<DeployConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isDeploying, setIsDeploying] = useState<string | null>(null);
  const [newConfig, setNewConfig] = useState({ name: '', domain: '', repo: '' });
  const [showNewConfigForm, setShowNewConfigForm] = useState(false);
  const [isCreatingVM, setIsCreatingVM] = useState(false);
  const [newVMName, setNewVMName] = useState('');

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
      setVms(data.filter((vm: VMInstance) => vm.status === 'ready'));
    } catch (error: any) {
      console.error('Ошибка загрузки VM:', error);
    }
  };

  const loadConfigs = async () => {
    try {
      const resp = await fetch(API_ENDPOINTS.deployConfig);
      const data = await resp.json();
      setConfigs(data);
    } catch (error: any) {
      console.error('Ошибка загрузки конфигов:', error);
    }
  };

  const handleDeploy = async (configName: string) => {
    setIsDeploying(configName);
    try {
      const resp = await fetch(API_ENDPOINTS.deploy, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ config_name: configName, type: 'all' })
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка деплоя");
      }

      toast({
        title: "✅ Деплой запущен!",
        description: data.logs ? data.logs.join('\n') : "Проект разворачивается на сервере"
      });
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsDeploying(null);
    }
  };

  const handleCreateConfig = async () => {
    if (!newConfig.name || !newConfig.domain || !newConfig.repo) {
      toast({
        title: "Ошибка",
        description: "Заполни все поля",
        variant: "destructive"
      });
      return;
    }

    if (vms.length === 0) {
      toast({
        title: "Ошибка",
        description: "Нет доступных серверов",
        variant: "destructive"
      });
      return;
    }

    try {
      const resp = await fetch(API_ENDPOINTS.deployConfig, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newConfig.name,
          domain: newConfig.domain,
          github_repo: newConfig.repo,
          vm_instance_id: vms[0].id
        })
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка создания конфига");
      }

      toast({
        title: "✅ Конфиг создан!",
        description: `Теперь можно задеплоить ${newConfig.domain}`
      });

      setNewConfig({ name: '', domain: '', repo: '' });
      setShowNewConfigForm(false);
      loadConfigs();
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    }
  };

  const handleDeleteConfig = async (name: string) => {
    if (!confirm(`Удалить конфиг ${name}?`)) return;

    try {
      const resp = await fetch(`${API_ENDPOINTS.deployConfig}?name=${name}`, {
        method: "DELETE"
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка удаления");
      }

      toast({
        title: "✅ Удалено",
        description: `Конфиг ${name} удалён`
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

  const handleCreateVM = async () => {
    if (!newVMName) {
      toast({
        title: "Ошибка",
        description: "Введи название VM",
        variant: "destructive"
      });
      return;
    }

    setIsCreatingVM(true);
    try {
      const resp = await fetch(API_ENDPOINTS.vmCreate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: newVMName
        })
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка создания VM");
      }

      toast({
        title: "✅ VM создаётся!",
        description: data.message || `VM ${newVMName} создаётся, это займёт 1-2 минуты`
      });

      setNewVMName('');
      setTimeout(() => loadVMs(), 3000);
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsCreatingVM(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center">
        <div className="text-white text-xl">Загрузка...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-5xl py-8 space-y-6">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-white">🚀 Деплой проектов</h1>
          <p className="text-slate-300">Управляй серверами и деплоем</p>
        </div>

        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white flex items-center gap-2">
                <Icon name="Server" className="h-5 w-5 text-green-400" />
                Серверы
              </CardTitle>
              <div className="flex gap-2">
                <Input
                  value={newVMName}
                  onChange={(e) => setNewVMName(e.target.value)}
                  placeholder="Название VM"
                  className="bg-slate-800 border-slate-700 text-white w-40"
                />
                <Button 
                  onClick={handleCreateVM}
                  disabled={isCreatingVM}
                  size="sm"
                  className="bg-green-600 hover:bg-green-700"
                >
                  {isCreatingVM ? (
                    <Icon name="Loader2" className="h-4 w-4 animate-spin" />
                  ) : (
                    <>
                      <Icon name="Plus" className="mr-2 h-4 w-4" />
                      Создать VM
                    </>
                  )}
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {vms.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                Нет серверов. Создай VM через Yandex Cloud.
              </div>
            ) : (
              <div className="grid gap-3">
                {vms.map(vm => (
                  <div key={vm.id} className="bg-slate-900/50 rounded-lg p-4 flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <Icon name="CheckCircle" className="h-5 w-5 text-green-400" />
                      <div>
                        <div className="text-white font-semibold">{vm.name}</div>
                        <div className="text-slate-400 text-sm font-mono">{vm.ip_address}</div>
                      </div>
                    </div>
                    <div className="text-green-400 text-sm">Готов</div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white">Конфиги деплоя</CardTitle>
              <Button 
                onClick={() => setShowNewConfigForm(!showNewConfigForm)}
                size="sm"
                className="bg-blue-600 hover:bg-blue-700"
              >
                <Icon name="Plus" className="mr-2 h-4 w-4" />
                Новый конфиг
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {showNewConfigForm && (
              <div className="bg-slate-900/50 rounded-lg p-4 space-y-3 border border-blue-500/30">
                <div className="grid gap-3">
                  <div>
                    <Label className="text-slate-300">Название</Label>
                    <Input
                      value={newConfig.name}
                      onChange={(e) => setNewConfig({...newConfig, name: e.target.value})}
                      placeholder="production"
                      className="bg-slate-800 border-slate-700 text-white"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">Домен</Label>
                    <Input
                      value={newConfig.domain}
                      onChange={(e) => setNewConfig({...newConfig, domain: e.target.value})}
                      placeholder="example.com"
                      className="bg-slate-800 border-slate-700 text-white"
                    />
                  </div>
                  <div>
                    <Label className="text-slate-300">GitHub репозиторий</Label>
                    <Input
                      value={newConfig.repo}
                      onChange={(e) => setNewConfig({...newConfig, repo: e.target.value})}
                      placeholder="username/repo"
                      className="bg-slate-800 border-slate-700 text-white"
                    />
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button onClick={handleCreateConfig} className="bg-green-600 hover:bg-green-700">
                    <Icon name="Check" className="mr-2 h-4 w-4" />
                    Создать
                  </Button>
                  <Button onClick={() => setShowNewConfigForm(false)} variant="outline" className="border-slate-600">
                    Отмена
                  </Button>
                </div>
              </div>
            )}

            {configs.length === 0 ? (
              <div className="text-center py-8 text-slate-400">
                Нет конфигов. Создай первый конфиг для деплоя.
              </div>
            ) : (
              <div className="grid gap-3">
                {configs.map(config => (
                  <div key={config.id} className="bg-slate-900/50 rounded-lg p-4 border border-slate-700">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex-1">
                        <div className="text-white font-semibold text-lg mb-1">{config.domain}</div>
                        <div className="text-slate-400 text-sm mb-2">{config.github_repo}</div>
                        <div className="flex gap-4 text-xs text-slate-500">
                          <span>Конфиг: {config.name}</span>
                          {config.vm_ip && <span>IP: {config.vm_ip}</span>}
                        </div>
                      </div>
                      <Button
                        onClick={() => handleDeleteConfig(config.name)}
                        size="sm"
                        variant="ghost"
                        className="text-red-400 hover:text-red-300 hover:bg-red-950/50"
                      >
                        <Icon name="Trash2" className="h-4 w-4" />
                      </Button>
                    </div>
                    <Button
                      onClick={() => handleDeploy(config.name)}
                      disabled={isDeploying === config.name}
                      className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700"
                    >
                      {isDeploying === config.name ? (
                        <>
                          <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                          Деплою...
                        </>
                      ) : (
                        <>
                          <Icon name="Rocket" className="mr-2 h-4 w-4" />
                          Задеплоить
                        </>
                      )}
                    </Button>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}