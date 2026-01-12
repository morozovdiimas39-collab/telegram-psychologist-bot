import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { useToast } from "@/hooks/use-toast";
import Icon from "@/components/ui/icon";

const Deploy = () => {
  const [githubUrl, setGithubUrl] = useState("");
  const [projectName, setProjectName] = useState("");
  const [domain, setDomain] = useState("");
  const [isDeploying, setIsDeploying] = useState(false);
  const [deployLog, setDeployLog] = useState<string[]>([]);
  const [isCreatingVM, setIsCreatingVM] = useState(false);
  const [vmIp, setVmIp] = useState("");
  const [vmWebhook, setVmWebhook] = useState("");
  const [vmSshKey, setVmSshKey] = useState("");
  const [showVmSecrets, setShowVmSecrets] = useState(false);
  const [isUpdatingVM, setIsUpdatingVM] = useState(false);
  const [isRestartingVM, setIsRestartingVM] = useState(false);
  const { toast } = useToast();

  const handleCreateVM = async () => {
    setIsCreatingVM(true);
    setDeployLog(["🚀 Создаю VM в Yandex Cloud..."]);

    try {
      const response = await fetch("https://functions.poehali.dev/473a90f3-4df5-49e2-8d37-930288a2b3eb", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const data = await response.json();

      if (response.ok || response.status === 202) {
        setDeployLog(prev => [...prev, ...data.logs]);
        
        if (data.ip && data.webhook) {
          setVmIp(data.ip);
          setVmWebhook(data.webhook);
          setShowVmSecrets(true);
          
          setDeployLog(prev => [
            ...prev,
            "",
            "✅ VM готова!",
            `📋 IP адрес: ${data.ip}`,
            `📋 Webhook: ${data.webhook}`,
            "",
            "💡 Добавь секреты в проект:",
            `VM_IP_ADDRESS = ${data.ip}`,
            `VM_WEBHOOK_URL = ${data.webhook}`
          ]);
          
          toast({
            title: "✅ VM создана!",
            description: "Добавь секреты VM_IP_ADDRESS и VM_WEBHOOK_URL"
          });
        } else {
          toast({
            title: "⏳ VM создаётся",
            description: "Повтори запрос через минуту"
          });
        }
      } else {
        throw new Error(data.error || "Ошибка создания VM");
      }
    } catch (error: any) {
      setDeployLog(prev => [...prev, `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsCreatingVM(false);
    }
  };

  const handleUpdateVM = async () => {
    setIsUpdatingVM(true);
    setDeployLog(["🔄 Обновляю скрипт деплоя на VM..."]);

    try {
      const response = await fetch("https://functions.poehali.dev/8bc9a2dc-aa30-4e12-90da-aafc88c6dc5e", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const data = await response.json();

      if (response.ok) {
        setDeployLog(prev => [...prev, ...data.logs]);
        toast({
          title: "✅ VM обновлена!",
          description: "Скрипт деплоя с поддержкой БД и функций установлен"
        });
      } else {
        throw new Error(data.error || "Ошибка обновления VM");
      }
    } catch (error: any) {
      setDeployLog(prev => [...prev, `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsUpdatingVM(false);
    }
  };

  const handleRestartVM = async () => {
    setIsRestartingVM(true);
    setDeployLog(["🔄 Перезагружаю VM..."]);

    try {
      const response = await fetch("https://functions.poehali.dev/d562c906-3f9a-4041-a2f7-05605e206246", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });

      const data = await response.json();

      if (response.ok) {
        setDeployLog(prev => [...prev, ...data.logs]);
        toast({
          title: "✅ VM перезагружается!",
          description: "Жди 2 минуты, webhook запустится автоматически"
        });
      } else {
        throw new Error(data.error || "Ошибка перезагрузки VM");
      }
    } catch (error: any) {
      setDeployLog(prev => [...prev, `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsRestartingVM(false);
    }
  };

  const handleDeploy = async () => {
    if (!githubUrl || !projectName || !domain) {
      toast({
        title: "Ошибка",
        description: "Заполните все обязательные поля",
        variant: "destructive"
      });
      return;
    }

    setIsDeploying(true);
    setDeployLog(["🚀 Начинаю деплой..."]);

    try {
      const response = await fetch("https://functions.poehali.dev/aa6cb973-aa73-426a-8148-f1be1cbf3a3b", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          githubUrl,
          projectName,
          domain
        })
      });

      const data = await response.json();

      if (response.ok) {
        setDeployLog(prev => [...prev, ...data.logs]);
        toast({
          title: "✅ Успешно!",
          description: `Проект развернут на ${domain}`
        });
      } else {
        throw new Error(data.error || "Ошибка деплоя");
      }
    } catch (error: any) {
      setDeployLog(prev => [...prev, `❌ Ошибка: ${error.message}`]);
      toast({
        title: "Ошибка деплоя",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsDeploying(false);
    }
  };

  return (
    <div className="min-h-screen bg-background p-4">
      <div className="container mx-auto max-w-4xl py-8 space-y-8">
        <div className="text-center space-y-4">
          <h1 className="text-4xl font-bold">Деплой проектов из poehali.dev</h1>
          <p className="text-muted-foreground">
            Автоматический перенос проектов в Yandex Cloud
          </p>
          <div className="flex gap-4 justify-center">
            <Button
              onClick={handleCreateVM}
              disabled={isCreatingVM}
              size="lg"
              variant="outline"
            >
              {isCreatingVM ? (
                <>
                  <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                  Создаю VM...
                </>
              ) : (
                <>
                  <Icon name="Server" className="mr-2 h-4 w-4" />
                  Создать VM в Yandex Cloud
                </>
              )}
            </Button>
            
            <Button
              onClick={handleUpdateVM}
              disabled={isUpdatingVM}
              size="lg"
            >
              {isUpdatingVM ? (
                <>
                  <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                  Обновляю VM...
                </>
              ) : (
                <>
                  <Icon name="RefreshCw" className="mr-2 h-4 w-4" />
                  Обновить скрипт деплоя
                </>
              )}
            </Button>

            <Button
              onClick={() => window.open('https://functions.poehali.dev/a337e260-916c-4d7b-a103-b487dc06efe8', '_blank')}
              size="lg"
              variant="destructive"
            >
              <Icon name="Trash2" className="mr-2 h-4 w-4" />
              1. Удалить VM
            </Button>

            <Button
              onClick={() => window.open('https://functions.poehali.dev/2ad40487-21a0-4145-b7ac-6bc414b3b82b', '_blank')}
              size="lg"
              variant="default"
            >
              <Icon name="Plus" className="mr-2 h-4 w-4" />
              2. Создать VM с SSH
            </Button>

            <Button
              onClick={() => window.open('https://functions.poehali.dev/f3c33704-629c-4797-8313-284016acb44c', '_blank')}
              size="lg"
              variant="secondary"
            >
              <Icon name="Zap" className="mr-2 h-4 w-4" />
              Запустить webhook
            </Button>
          </div>
        </div>

        {showVmSecrets && (
          <Card className="border-primary">
            <CardHeader>
              <CardTitle>Секреты VM</CardTitle>
              <CardDescription>
                Скопируйте эти значения — они понадобятся для деплоя
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="vm-ip">VM_IP_ADDRESS</Label>
                <Input
                  id="vm-ip"
                  value={vmIp}
                  readOnly
                  className="font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vm-webhook">VM_WEBHOOK_URL</Label>
                <Input
                  id="vm-webhook"
                  value={vmWebhook}
                  readOnly
                  className="font-mono"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="vm-ssh-key">VM_SSH_KEY</Label>
                <textarea
                  id="vm-ssh-key"
                  value={vmSshKey}
                  onChange={(e) => setVmSshKey(e.target.value)}
                  placeholder="Вставь SSH ключ сюда после создания VM"
                  className="w-full h-32 px-3 py-2 text-sm border rounded-md font-mono"
                />
              </div>
            </CardContent>
          </Card>
        )}

        <Card>
          <CardHeader>
            <CardTitle>Параметры деплоя</CardTitle>
            <CardDescription>
              Заполните данные для развертывания проекта
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="github">
                GitHub URL <span className="text-destructive">*</span>
              </Label>
              <Input
                id="github"
                placeholder="https://github.com/username/repo"
                value={githubUrl}
                onChange={(e) => setGithubUrl(e.target.value)}
                disabled={isDeploying}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="project">
                Название проекта <span className="text-destructive">*</span>
              </Label>
              <Input
                id="project"
                placeholder="myproject (только латиница и дефис)"
                value={projectName}
                onChange={(e) => setProjectName(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ""))}
                disabled={isDeploying}
              />
              <p className="text-xs text-muted-foreground">
                Используется для создания базы данных и контейнера
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="domain">
                Домен <span className="text-destructive">*</span>
              </Label>
              <Input
                id="domain"
                placeholder="example.ru"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                disabled={isDeploying}
              />
              <p className="text-xs text-muted-foreground">
                DNS нужно настроить на IP сервера вручную
              </p>
            </div>

            <div className="space-y-2">
              <div className="rounded-lg border p-4 bg-muted/50">
                <p className="text-sm font-medium mb-2">🔐 Секреты проекта</p>
                <p className="text-xs text-muted-foreground">
                  Все секреты из poehali.dev автоматически перенесутся на VM.
                  Облачные функции и база данных будут работать так же, как в poehali.dev.
                </p>
              </div>
            </div>

            <Button
              onClick={handleDeploy}
              disabled={isDeploying}
              size="lg"
              className="w-full"
            >
              {isDeploying ? (
                <>
                  <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                  Деплой в процессе...
                </>
              ) : (
                <>
                  <Icon name="Rocket" className="mr-2 h-4 w-4" />
                  Развернуть проект
                </>
              )}
            </Button>
          </CardContent>
        </Card>

        {deployLog.length > 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Лог деплоя</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="bg-muted rounded-lg p-4 font-mono text-sm space-y-1 max-h-96 overflow-y-auto">
                {deployLog.map((log, idx) => (
                  <div key={idx}>{log}</div>
                ))}
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="vm-ssh-key">VM_SSH_KEY (вставь сюда ключ из логов выше)</Label>
                <textarea
                  id="vm-ssh-key"
                  value={vmSshKey}
                  onChange={(e) => setVmSshKey(e.target.value)}
                  placeholder="-----BEGIN RSA PRIVATE KEY-----
...вставь SSH ключ из логов выше...
-----END RSA PRIVATE KEY-----"
                  className="w-full h-32 px-3 py-2 text-sm border rounded-md font-mono bg-background"
                />
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default Deploy;