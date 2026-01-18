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
  const [vms, setVms] = useState<VMInstance[]>([]);
  const [configs, setConfigs] = useState<DeployConfig[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAddingVM, setIsAddingVM] = useState(false);

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
      setVms(data.filter((vm: VMInstance) => vm.status !== 'error'));
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

  const handleAddMyServer = async () => {
    setIsAddingVM(true);
    try {
      const resp = await fetch(API_ENDPOINTS.vmCreate, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "my-server",
          existing_vm: true
        })
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка добавления сервера");
      }

      toast({
        title: "✅ Сервер добавлен!",
        description: `IP: ${data.ip_address} готов к деплою`
      });

      loadVMs();
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsAddingVM(false);
    }
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 flex items-center justify-center">
        <div className="text-white text-xl">Загрузка...</div>
      </div>
    );
  }

  const hasVM = vms.length > 0 && vms[0].status === 'ready';

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-4xl py-8 space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold text-white">🚀 Деплой на свой сервер</h1>
          <p className="text-slate-300 text-lg">
            Просто и быстро
          </p>
        </div>

        {!hasVM ? (
          <Card className="bg-white/10 backdrop-blur border-white/20">
            <CardHeader>
              <CardTitle className="text-white text-2xl">Шаг 1: Добавь свой сервер</CardTitle>
              <CardDescription className="text-slate-300 text-base">
                У тебя уже есть настроенный сервер. Просто добавь его в систему.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="bg-slate-900/50 rounded-lg p-6 border border-green-500/30">
                <div className="flex items-start gap-4">
                  <div className="text-4xl">✅</div>
                  <div className="flex-1">
                    <h3 className="text-white font-semibold text-lg mb-2">Твой сервер готов</h3>
                    <ul className="space-y-2 text-slate-300">
                      <li className="flex items-center gap-2">
                        <Icon name="Check" className="h-4 w-4 text-green-400" />
                        <span>IP адрес сохранён в секретах</span>
                      </li>
                      <li className="flex items-center gap-2">
                        <Icon name="Check" className="h-4 w-4 text-green-400" />
                        <span>SSH ключ настроен</span>
                      </li>
                      <li className="flex items-center gap-2">
                        <Icon name="Check" className="h-4 w-4 text-green-400" />
                        <span>Nginx, Bun, SSL установлены</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>

              <Button
                onClick={handleAddMyServer}
                disabled={isAddingVM}
                size="lg"
                className="w-full bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-lg py-6"
              >
                {isAddingVM ? (
                  <>
                    <Icon name="Loader2" className="mr-2 h-5 w-5 animate-spin" />
                    Добавляю сервер...
                  </>
                ) : (
                  <>
                    <Icon name="Plus" className="mr-2 h-5 w-5" />
                    Добавить мой сервер
                  </>
                )}
              </Button>

              <div className="text-xs text-slate-400 text-center">
                Это займёт 1 секунду. Сервер будет готов к деплою сразу.
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="space-y-6">
            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white flex items-center gap-2">
                  <Icon name="Server" className="h-5 w-5 text-green-400" />
                  Твой сервер
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="bg-slate-900/50 rounded-lg p-4 space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Название:</span>
                    <span className="text-white font-semibold">{vms[0].name}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">IP адрес:</span>
                    <span className="text-white font-mono">{vms[0].ip_address}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-slate-400">Статус:</span>
                    <span className="text-green-400 flex items-center gap-2">
                      <Icon name="CheckCircle" className="h-4 w-4" />
                      Готов к деплою
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-white/10 backdrop-blur border-white/20">
              <CardHeader>
                <CardTitle className="text-white">Что дальше?</CardTitle>
                <CardDescription className="text-slate-300">
                  Выбери что хочешь сделать
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-4">
                  <div className="bg-slate-900/50 rounded-lg p-4 border border-blue-500/30">
                    <div className="flex items-start gap-4">
                      <div className="text-3xl">📦</div>
                      <div className="flex-1">
                        <h3 className="text-white font-semibold mb-1">Деплой проекта</h3>
                        <p className="text-slate-400 text-sm mb-3">
                          Загрузи свой проект на сервер с автоматической настройкой
                        </p>
                        <Button className="bg-blue-600 hover:bg-blue-700">
                          <Icon name="Upload" className="mr-2 h-4 w-4" />
                          Задеплоить проект
                        </Button>
                      </div>
                    </div>
                  </div>

                  <div className="bg-slate-900/50 rounded-lg p-4 border border-purple-500/30">
                    <div className="flex items-start gap-4">
                      <div className="text-3xl">🌐</div>
                      <div className="flex-1">
                        <h3 className="text-white font-semibold mb-1">Настроить домен</h3>
                        <p className="text-slate-400 text-sm mb-3">
                          Привяжи свой домен и получи SSL сертификат
                        </p>
                        <Button variant="outline" className="border-purple-500 text-purple-400">
                          <Icon name="Globe" className="mr-2 h-4 w-4" />
                          Добавить домен
                        </Button>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="text-xs text-slate-400 border-t border-white/10 pt-4">
                  <p className="mb-2"><strong>💡 Совет:</strong> Начни с деплоя проекта. Домен можно настроить потом.</p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}
      </div>
    </div>
  );
}
