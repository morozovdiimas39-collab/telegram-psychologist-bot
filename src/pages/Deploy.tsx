import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { useToast } from "@/hooks/use-toast";
import Icon from "@/components/ui/icon";
import { API_ENDPOINTS } from "@/lib/api";
import { MIGRATE_URL } from "@/lib/migrate-url";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

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
  database_url?: string | null;
  database_vm_id?: number | null;
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
  const [newConfig, setNewConfig] = useState({ name: "", domain: "", repo: "", github_token: "", database_url: "", database_vm_id: null as number | null });
  const [showNewConfigForm, setShowNewConfigForm] = useState(false);
  const [isCreatingVM, setIsCreatingVM] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const [editingConfig, setEditingConfig] = useState<string | null>(null);
  const [editConfig, setEditConfig] = useState({ name: "", domain: "", repo: "", vmId: 0, github_token: "", database_url: "", database_vm_id: null as number | null });
  const [selectedVmId, setSelectedVmId] = useState<number | null>(null);
  const [isCreateVmDialogOpen, setIsCreateVmDialogOpen] = useState(false);
  const [newVmName, setNewVmName] = useState("");
  const [deployLogs, setDeployLogs] = useState<string[] | null>(null);
  const [isDeployLogsOpen, setIsDeployLogsOpen] = useState(false);
  const [deployLogsTitle, setDeployLogsTitle] = useState<string | null>(null);
  const [isDeployingFunctions, setIsDeployingFunctions] = useState<string | null>(null);
  const [deployedFunctions, setDeployedFunctions] = useState<{ name: string; url: string }[]>([]);
  const [isMigrating, setIsMigrating] = useState<string | null>(null);
  const [isSettingUpSsl, setIsSettingUpSsl] = useState<string | null>(null);
  const [sshKeyDialog, setSshKeyDialog] = useState<{ open: boolean; vm: VMInstance | null; sshKey: string | null }>({ open: false, vm: null, sshKey: null });
  const [isLoadingSshKey, setIsLoadingSshKey] = useState(false);
  const [deleteVmDialog, setDeleteVmDialog] = useState<{ open: boolean; vm: VMInstance | null }>({ open: false, vm: null });
  const [isDeletingVm, setIsDeletingVm] = useState(false);
  const [addSshKeyDialog, setAddSshKeyDialog] = useState<{ open: boolean; vm: VMInstance | null; keyValue: string }>({ open: false, vm: null, keyValue: '' });
  const [isSavingSshKey, setIsSavingSshKey] = useState(false);
  const [isSettingUpDatabase, setIsSettingUpDatabase] = useState(false);
  const [databaseSetupResult, setDatabaseSetupResult] = useState<{ database_url: string; db_password: string } | null>(null);

  useEffect(() => {
    // При первой загрузке сразу синхронизируем с Yandex Cloud
    const init = async () => {
      try {
        await fetch(API_ENDPOINTS.ycSync, { method: 'POST' });
      } catch (e) {
        console.error('Sync error:', e);
      }
      loadData();
    };
    init();
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
      
      // Проверяем что data это массив
      if (!Array.isArray(data)) {
        console.error('Ошибка: VM list не является массивом', data);
        setVms([]);
        return;
      }
      
      // Показываем только актуальные VM (есть в Yandex Cloud)
      setVms(data.filter((vm: VMInstance) => 
        vm.yandex_vm_id && 
        vm.status !== 'error' && 
        vm.status !== 'deleted'
      ));
    } catch (error: any) {
      console.error('Ошибка загрузки VM:', error);
      setVms([]);
    }
  };

  const loadConfigs = async () => {
    try {
      const resp = await fetch(API_ENDPOINTS.deployConfig);
      const data = await resp.json();
      
      // Проверяем что data это массив
      if (!Array.isArray(data)) {
        console.error('Ошибка: Configs list не является массивом', data);
        setConfigs([]);
        return;
      }
      
      console.log('Загружено конфигов:', data.length);
      setConfigs(data);
    } catch (error: any) {
      console.error('Ошибка загрузки конфигов:', error);
      setConfigs([]);
    }
  };

  const handleDeploy = async (configName: string) => {
    setIsDeploying(configName);
    try {
      let token = "";
      try {
        token = localStorage.getItem(`deploy_github_token_${configName}`) || "";
      } catch {}
      const resp = await fetch(API_ENDPOINTS.deployLong, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          config_name: configName,
          ...(token.trim() ? { github_token: token.trim() } : {}),
        })
      });

      const data = await resp.json();

      if (!resp.ok) {
        // Показываем подробные логи деплоя, если они есть
        if (data.logs && Array.isArray(data.logs)) {
          setDeployLogs(data.logs);
          setDeployLogsTitle(`Ошибка деплоя: ${configName}`);
          setIsDeployLogsOpen(true);
        }

        toast({
          title: "Ошибка",
          description: data.error || "Ошибка деплоя",
          variant: "destructive",
        });
        return;
      }

      toast({
        title: "✅ Деплой запущен",
        description: data.url
          ? `Сборка идёт в фоне (2–3 минуты). Потом открой: ${data.url}`
          : "Сборка идёт в фоне (2–3 минуты). Обнови страницу позже.",
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

  const handleSetupSsl = async (configName: string) => {
    const sslUrl = API_ENDPOINTS.setupSsl;
    if (!sslUrl) {
      toast({
        title: "Настрой setup-ssl",
        description: "Задеплой backend/setup-ssl в Yandex Cloud и добавь URL в src/lib/setup-ssl-url.ts. См. DEPLOY_SETUP_SSL.md",
        variant: "destructive"
      });
      return;
    }
    setIsSettingUpSsl(configName);
    try {
      const resp = await fetch(`${sslUrl}?config_name=${encodeURIComponent(configName)}`, {
        method: "GET"
      });
      const data = await resp.json();
      if (data.logs && Array.isArray(data.logs)) {
        setDeployLogs(data.logs);
        setDeployLogsTitle(`Установка SSL: ${configName}`);
        setIsDeployLogsOpen(true);
      }
      if (resp.ok) {
        toast({ title: "✅ SSL", description: data.url ? `Готово: ${data.url}` : "Сертификат установлен" });
      } else {
        toast({ title: "Ошибка SSL", description: data.error || "Проверь логи", variant: "destructive" });
      }
    } catch (error: any) {
      toast({ title: "Ошибка", description: error.message, variant: "destructive" });
    } finally {
      setIsSettingUpSsl(null);
    }
  };

  const handleDeployFunctions = async (config: DeployConfig) => {
    setIsDeployingFunctions(config.name);
    setDeployLogs(null);
    setDeployedFunctions([]);
    try {
      const allLogs: string[] = [];
      const batchSize = 5;
      let offset = 0;
      let batchIndex = 1;
      let hasMore = true;
      let totalDeployed = 0;
      let totalFunctions: number | null = null;
       const functionsMap: Record<string, string> = {};

      while (hasMore) {
        const resp = await fetch(API_ENDPOINTS.deployFunctions, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            github_repo: config.github_repo,
            secrets: [],
            offset,
            batch_size: batchSize,
          }),
        });

        const data = await resp.json();

        if (data.logs && Array.isArray(data.logs)) {
          allLogs.push(`\n=== Пачка ${batchIndex} (offset ${offset}) ===`, ...data.logs);
        }

        if (data.function_urls && typeof data.function_urls === "object") {
          Object.entries<string>(data.function_urls as Record<string, string>).forEach(
            ([name, url]) => {
              if (typeof url === "string") {
                functionsMap[name] = url;
              }
            }
          );
        }

        if (!resp.ok) {
          setDeployLogs(allLogs);
          setDeployLogsTitle(`Ошибка backend-функций: ${config.github_repo}`);
          setIsDeployLogsOpen(true);

          const list = Object.entries(functionsMap)
            .map(([name, url]) => ({ name, url }))
            .sort((a, b) => a.name.localeCompare(b.name));
          setDeployedFunctions(list);

          toast({
            title: "Ошибка деплоя backend-функций",
            description: data.error || "Не удалось задеплоить backend-функции",
            variant: "destructive",
          });
          return;
        }

        if (Array.isArray(data.deployed)) {
          totalDeployed += data.deployed.length;
        }
        if (typeof data.total_functions === "number") {
          totalFunctions = data.total_functions;
        }

        hasMore = Boolean(data.has_more);
        if (!hasMore) break;

        offset = typeof data.next_offset === "number" ? data.next_offset : offset + batchSize;
        batchIndex += 1;

        if (batchIndex > 20) {
          hasMore = false;
          allLogs.push("\n⚠️ Остановлено на клиенте из-за слишком большого количества пачек.");
        }
      }

      const list = Object.entries(functionsMap)
        .map(([name, url]) => ({ name, url }))
        .sort((a, b) => a.name.localeCompare(b.name));
      setDeployedFunctions(list);

      if (allLogs.length > 0) {
        setDeployLogs(allLogs);
        setDeployLogsTitle(`Backend-функции: ${config.github_repo}`);
        setIsDeployLogsOpen(true);
      }

      toast({
        title: "✅ Backend-функции задеплоены",
        description:
          totalFunctions !== null
            ? `Задеплоено функций: ${totalDeployed} из ${totalFunctions} (репозиторий ${config.github_repo})`
            : `Задеплоено функций: ${totalDeployed} (репозиторий ${config.github_repo})`,
      });
    } catch (error: any) {
      toast({
        title: "Ошибка деплоя backend-функций",
        description: error.message,
        variant: "destructive",
      });
    } finally {
      setIsDeployingFunctions(null);
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

    const vmId = selectedVmId || vms[0].id;

    try {
      const createData = {
        name: newConfig.name,
        domain: newConfig.domain,
        github_repo: newConfig.repo,
        vm_instance_id: vmId || null,
        database_url: newConfig.database_url?.trim() || null,
        database_vm_id: newConfig.database_vm_id || null
      };
      
      
      const resp = await fetch(API_ENDPOINTS.deployConfig, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(createData)
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка создания конфига");
      }

      toast({
        title: "✅ Конфиг создан!",
        description: `Теперь можно задеплоить ${newConfig.domain}`
      });

      if (newConfig.github_token) {
        try { localStorage.setItem(`deploy_github_token_${newConfig.name}`, newConfig.github_token); } catch {}
      }
      setNewConfig({ name: '', domain: '', repo: '', github_token: '', database_url: '', database_vm_id: null });
      setSelectedVmId(null);
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

  const handleEditConfig = async (configName: string) => {
    try {
      const updateData: any = {
        old_name: configName,
        name: editConfig.name,
        domain: editConfig.domain,
        github_repo: editConfig.repo,
        vm_instance_id: editConfig.vmId || null,
        database_url: editConfig.database_url?.trim() || null,
        database_vm_id: editConfig.database_vm_id || null
      };
      
      
      const resp = await fetch(API_ENDPOINTS.deployConfig, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updateData)
      });

      const data = await resp.json();

      if (!resp.ok) {
        console.error('Ошибка сохранения конфига:', data);
        throw new Error(data.error || "Ошибка обновления");
      }

      console.log('Конфиг успешно сохранён:', data);
      toast({
        title: "✅ Конфиг обновлён!",
        description: `${configName} успешно изменён`
      });

      if (editConfig.github_token) {
        try { localStorage.setItem(`deploy_github_token_${editConfig.name}`, editConfig.github_token); } catch {}
      }
      setEditingConfig(null);
      loadConfigs();
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    }
  };

  const startEdit = (config: DeployConfig) => {
    setEditingConfig(config.name);
    let token = "";
    try { 
      token = localStorage.getItem(`deploy_github_token_${config.name}`) || ""; 
      console.log(`Загружаю токен для конфига "${config.name}":`, token ? 'найден' : 'не найден');
    } catch (e) {
      console.error('Ошибка загрузки токена:', e);
    }
    setEditConfig({
      name: config.name,
      domain: config.domain,
      repo: config.github_repo,
      vmId: config.vm_instance_id || 0,
      github_token: token,
      database_url: config.database_url || '',
      database_vm_id: config.database_vm_id || 0
    });
  };

  const handleCreateVM = async () => {
    setIsCreatingVM(true);
    try {
      const resp = await fetch(API_ENDPOINTS.vmSetup, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          name: newVmName.trim() || undefined 
        })
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка создания сервера");
      }

      toast({
        title: "✅ Сервер создан!",
        description: `IP: ${data.ip_address} - готов к деплою`
      });

      loadVMs();
      setIsCreateVmDialogOpen(false);
      setNewVmName("");
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

  const handleGetSshKey = async (vm: VMInstance) => {
    setIsLoadingSshKey(true);
    try {
      // Пробуем получить через новый endpoint, если он есть
      let sshKeyUrl = API_ENDPOINTS.vmSshKey;
      if (!sshKeyUrl) {
        // Fallback: используем vm-list с параметром id
        sshKeyUrl = `${API_ENDPOINTS.vmList}?id=${vm.id}`;
      } else {
        sshKeyUrl = `${sshKeyUrl}?id=${vm.id}`;
      }

      const resp = await fetch(sshKeyUrl);
      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка получения SSH ключа");
      }

      // Если это vm-list, ключа там нет, пробуем другой способ
      if (!data.ssh_private_key && data.id) {
        // Пробуем через vm-list с полным запросом
        const fullResp = await fetch(`${API_ENDPOINTS.vmList}?id=${vm.id}`);
        const fullData = await fullResp.json();
        if (fullData.ssh_private_key) {
          setSshKeyDialog({ open: true, vm, sshKey: fullData.ssh_private_key });
          return;
        }
        throw new Error("SSH ключ не найден. Убедись что функция vm-ssh-key задеплоена.");
      }

      setSshKeyDialog({ open: true, vm, sshKey: data.ssh_private_key });
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
      if (error.message?.includes('не найден') || error.message?.includes('SSH')) {
        setAddSshKeyDialog({ open: true, vm, keyValue: '' });
      }
    } finally {
      setIsLoadingSshKey(false);
    }
  };

  const handleSaveSshKeyToDb = async () => {
    if (!addSshKeyDialog.vm || !addSshKeyDialog.keyValue.trim()) {
      toast({ title: "Ошибка", description: "Вставь приватный SSH ключ", variant: "destructive" });
      return;
    }
    const key = addSshKeyDialog.keyValue.trim();
    if (!key.includes('BEGIN') || !key.includes('END')) {
      toast({ title: "Ошибка", description: "Ключ должен содержать -----BEGIN----- и -----END-----", variant: "destructive" });
      return;
    }
    setIsSavingSshKey(true);
    try {
      let resp = await fetch(API_ENDPOINTS.vmList, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: addSshKeyDialog.vm.id, ssh_private_key: key })
      });
      if (resp.status === 405) {
        resp = await fetch(API_ENDPOINTS.vmList, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'update_ssh_key', id: addSshKeyDialog.vm.id, ssh_private_key: key })
        });
      }
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || `Ошибка ${resp.status}`);
      toast({ title: "✅ Ключ сохранён", description: data.message || "SSH ключ сохранён в БД. Деплой теперь должен работать." });
      setAddSshKeyDialog({ open: false, vm: null, keyValue: '' });
    } catch (error: any) {
      toast({ title: "Ошибка", description: error.message, variant: "destructive" });
    } finally {
      setIsSavingSshKey(false);
    }
  };

  const handleDeleteVm = async () => {
    if (!deleteVmDialog.vm) return;
    
    // Проверяем, есть ли конфиги, привязанные к этой VM
    const linkedConfigs = configs.filter(c => c.vm_instance_id === deleteVmDialog.vm?.id);
    if (linkedConfigs.length > 0) {
      const configNames = linkedConfigs.map(c => c.name).join(', ');
      toast({
        title: "⚠️ Внимание",
        description: `К этой VM привязаны конфиги: ${configNames}. Они перестанут работать после удаления.`,
        variant: "destructive"
      });
      // Продолжаем удаление, но предупредили пользователя
    }
    
    setIsDeletingVm(true);
    try {
      const resp = await fetch(API_ENDPOINTS.vmList, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'delete', id: deleteVmDialog.vm.id }),
      });
      
      let data;
      try {
        data = await resp.json();
      } catch (e) {
        const text = await resp.text();
        throw new Error(`Ошибка парсинга ответа: ${text.substring(0, 200)}`);
      }
      
      if (!resp.ok) {
        throw new Error(data.error || `Ошибка удаления VM: ${resp.status} ${resp.statusText}`);
      }
      
      // Показываем логи если есть
      if (data.logs && data.logs.length > 0) {
        setDeployLogs(data.logs);
        setDeployLogsTitle(`Удаление VM: ${deleteVmDialog.vm.name}`);
        setIsDeployLogsOpen(true);
      }
      
      toast({
        title: "✅ VM удалена",
        description: data.message || `VM ${deleteVmDialog.vm.name} успешно удалена`,
      });
      
      // Обновляем список VM и конфигов
      await Promise.all([loadVMs(), loadConfigs()]);
      setDeleteVmDialog({ open: false, vm: null });
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsDeletingVm(false);
    }
  };

  const handleSetupDatabase = async () => {
    setIsSettingUpDatabase(true);
    setDatabaseSetupResult(null);
    
    // Проверяем есть ли endpoint
    if (!API_ENDPOINTS.setupDatabase) {
      toast({
        title: "Функция не задеплоена",
        description: "Сначала задеплой функцию setup-database через 'Деплой backend-функций'",
        variant: "destructive"
      });
      setIsSettingUpDatabase(false);
      return;
    }
    
    try {
      const resp = await fetch(API_ENDPOINTS.setupDatabase, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          db_name: 'deployer',
          db_user: 'deployer_user'
        })
      });
      
      let data;
      try {
        data = await resp.json();
      } catch (e) {
        const text = await resp.text();
        throw new Error(`Ошибка парсинга ответа: ${text.substring(0, 200)}`);
      }
      
      if (!resp.ok) {
        throw new Error(data.error || `Ошибка создания БД: ${resp.status}`);
      }
      
      // Показываем логи если есть
      if (data.logs && data.logs.length > 0) {
        setDeployLogs(data.logs);
        setDeployLogsTitle('Создание VM с PostgreSQL');
        setIsDeployLogsOpen(true);
      }
      
      if (data.database_url) {
        setDatabaseSetupResult({
          database_url: data.database_url,
          db_password: data.db_password || 'не указан'
        });
        
        toast({
          title: "✅ VM с PostgreSQL создана!",
          description: "Скопируй DATABASE_URL и добавь его во все функции",
        });
      } else {
        toast({
          title: "⚠️ VM создана, но DATABASE_URL не получен",
          description: "Проверь логи для деталей",
          variant: "destructive"
        });
      }
    } catch (error: any) {
      toast({
        title: "Ошибка создания БД",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsSettingUpDatabase(false);
    }
  };

  const handleSyncVMs = async () => {
    setIsSyncing(true);
    try {
      const resp = await fetch(API_ENDPOINTS.ycSync, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({})
      });

      const data = await resp.json();

      if (!resp.ok) {
        throw new Error(data.error || "Ошибка синхронизации");
      }

      toast({
        title: "✅ Синхронизация завершена",
        description: data.logs ? data.logs.join('\n') : `Обновлено ${data.updated} VM`
      });

      await loadVMs();
    } catch (error: any) {
      toast({
        title: "Ошибка",
        description: error.message,
        variant: "destructive"
      });
    } finally {
      setIsSyncing(false);
    }
  };

  const handleMigrate = async (config: DeployConfig) => {
    setIsMigrating(config.name);
    setDeployLogs(null);
    try {
      let token = "";
      try { 
        token = localStorage.getItem(`deploy_github_token_${config.name}`) || ""; 
        console.log(`Ищу токен для конфига: ${config.name}, найден:`, token ? 'да' : 'нет');
      } catch (e) {
        console.error('Ошибка чтения токена из localStorage:', e);
      }
      
      // Если токена нет в localStorage, пробуем найти по старому имени или другим вариантам
      if (!token || token.trim() === "") {
        // Пробуем найти токен по другим возможным ключам
        try {
          const allKeys = Object.keys(localStorage);
          const tokenKeys = allKeys.filter(key => key.startsWith('deploy_github_token_'));
          console.log('Все ключи токенов в localStorage:', tokenKeys);
          
          // Если есть только один токен, используем его
          if (tokenKeys.length === 1) {
            token = localStorage.getItem(tokenKeys[0]) || "";
            console.log('Использую единственный найденный токен');
          }
        } catch (e) {
          console.error('Ошибка поиска токена:', e);
        }
      }
      
      if (!token || token.trim() === "") {
        toast({
          title: "⚠️ Нет GitHub токена",
          description: `Добавь GitHub токен в конфиге "${config.name}" перед применением миграций. Открой конфиг для редактирования и вставь токен в поле "GitHub токен".`,
          variant: "destructive",
        });
        setIsMigrating(null);
        return;
      }
      
      const resp = await fetch(MIGRATE_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          github_repo: config.github_repo, 
          github_token: token.trim(),
          config_name: config.name  // Передаём config_name для получения database_url из конфига
        })
      });

      const data = await resp.json().catch(() => ({}));

      if (!resp.ok) {
        if (data.logs && Array.isArray(data.logs)) {
          setDeployLogs(data.logs);
          setDeployLogsTitle(`Ошибка миграций БД: ${config.github_repo}`);
          setIsDeployLogsOpen(true);
        }

        toast({
          title: "Ошибка применения миграций",
          description: data.error || "Не удалось применить миграции",
          variant: "destructive",
        });
        return;
      }

      if (data.logs && Array.isArray(data.logs)) {
        setDeployLogs(data.logs);
        setDeployLogsTitle(`Миграции БД: ${config.github_repo}`);
        setIsDeployLogsOpen(true);
      }

      toast({
        title: "✅ Миграции применены",
        description: data.applied_count
          ? `Применено: ${data.applied_count}, пропущено: ${data.skipped_count || 0}`
          : `Репозиторий: ${config.github_repo}`,
      });
    } catch (error: any) {
      const msg = error?.message || "Неизвестная ошибка";
      const hint = msg.includes("Failed to fetch") || msg.includes("fetch")
        ? "Проверь: 1) CORS в консоли браузера 2) URL функции в Yandex Cloud 3) Функция задеплоена?"
        : msg;
      toast({
        title: "Ошибка применения миграций",
        description: hint,
        variant: "destructive",
      });
    } finally {
      setIsMigrating(null);
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
        {/* Модалка логов деплоя */}
        <Dialog open={isDeployLogsOpen} onOpenChange={setIsDeployLogsOpen}>
          <DialogContent className="bg-slate-950 border-slate-800 text-white max-h-[80vh] flex flex-col">
            <DialogHeader>
              <DialogTitle>{deployLogsTitle || "Логи деплоя"}</DialogTitle>
              <DialogDescription className="text-slate-400">
                Полная история шагов деплоя с сервера. Скопируй этот текст, если нужно отправить его в поддержку.
              </DialogDescription>
            </DialogHeader>
            <div className="mt-2 flex-1 rounded-md bg-slate-900 border border-slate-800 overflow-auto">
              <pre className="whitespace-pre-wrap text-xs md:text-sm p-3 font-mono text-slate-100">
                {(deployLogs && deployLogs.length > 0)
                  ? deployLogs.join('\n')
                  : "Логи не получены от сервера."}
              </pre>
            </div>
            {deployedFunctions.length > 0 && (
              <div className="mt-4">
                <div className="text-sm text-slate-300 mb-2">
                  Выгруженные облачные функции (имя → URL):
                </div>
                <div className="rounded-md bg-slate-900 border border-slate-800 overflow-auto max-h-48">
                  <pre className="whitespace-pre-wrap text-xs md:text-sm p-3 font-mono text-slate-100">
                    {deployedFunctions.map((fn) => `${fn.name}: ${fn.url}`).join('\n')}
                  </pre>
                </div>
              </div>
            )}
            <DialogFooter className="pt-3">
              <Button
                type="button"
                variant="outline"
                className="border-slate-600 text-slate-200"
                onClick={() => setIsDeployLogsOpen(false)}
              >
                Закрыть
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <Dialog open={isCreateVmDialogOpen} onOpenChange={setIsCreateVmDialogOpen}>
          <DialogContent className="bg-slate-950 border-slate-800 text-white">
            <DialogHeader>
              <DialogTitle>Создать новый сервер</DialogTitle>
              <DialogDescription className="text-slate-400">
                Укажи понятное название сервера. Можно оставить поле пустым — имя будет сгенерировано автоматически.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-3 pt-2">
              <div>
                <Label className="text-slate-300">Название сервера</Label>
                <Input
                  autoFocus
                  value={newVmName}
                  onChange={(e) => setNewVmName(e.target.value)}
                  placeholder="prod-1, staging, test-bot"
                  className="bg-slate-900 border-slate-700 text-white"
                />
              </div>
            </div>
            <DialogFooter className="pt-4">
              <Button
                type="button"
                variant="outline"
                className="border-slate-600 text-slate-200"
                onClick={() => setIsCreateVmDialogOpen(false)}
                disabled={isCreatingVM}
              >
                Отмена
              </Button>
              <Button
                type="button"
                onClick={handleCreateVM}
                disabled={isCreatingVM}
                className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white"
              >
                {isCreatingVM ? (
                  <>
                    <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                    Создаю...
                  </>
                ) : (
                  <>
                    <Icon name="Plus" className="mr-2 h-4 w-4" />
                    Создать VM
                  </>
                )}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>

        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold text-white">🚀 Деплой проектов</h1>
          <p className="text-slate-300">Управляй серверами и деплоем</p>
          <div className="flex flex-wrap justify-center gap-2 mt-4">
            <Button
              onClick={() => window.location.href = '/setup'}
              variant="outline"
              className="border-yellow-500/50 hover:bg-yellow-950/30 text-yellow-300"
            >
              <Icon name="Settings" className="mr-2 h-4 w-4" />
              Настройка Yandex Cloud
            </Button>
            <Button
              onClick={() => window.location.href = '/migrate'}
              variant="outline"
              className="border-green-500/50 hover:bg-green-950/30 text-green-300"
            >
              <Icon name="Database" className="mr-2 h-4 w-4" />
              Миграции БД
            </Button>
            {configs.length > 0 && (
              <div className="flex items-center gap-2 pl-4 border-l border-emerald-500/30">
                <Icon name="Lock" className="h-4 w-4 text-emerald-400" />
                <select
                  id="ssl-header-select"
                  className="bg-slate-800 border border-emerald-500/50 text-white rounded px-3 py-2 text-sm min-w-[140px]"
                  defaultValue=""
                >
                  <option value="">Домен для SSL</option>
                  {configs.map(c => (
                    <option key={c.id} value={c.name}>{c.domain}</option>
                  ))}
                </select>
                <Button
                  size="sm"
                  onClick={() => {
                    const sel = document.getElementById('ssl-header-select') as HTMLSelectElement;
                    const name = sel?.value || configs[0]?.name;
                    if (name) handleSetupSsl(name);
                  }}
                  disabled={isSettingUpSsl !== null}
                  className="bg-emerald-600 hover:bg-emerald-700 text-white"
                >
                  {isSettingUpSsl ? <Icon name="Loader2" className="h-4 w-4 animate-spin" /> : 'Установить SSL'}
                </Button>
              </div>
            )}
          </div>
          
          {/* Кнопка автоматической настройки БД */}
          <div className="mt-4 bg-blue-950/30 border border-blue-500/30 rounded-lg p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-2">
                  <Icon name="Database" className="h-5 w-5 text-blue-400" />
                  <h3 className="text-white font-semibold">Автоматическая настройка БД</h3>
                </div>
                <p className="text-sm text-blue-200 mb-3">
                  Создай VM с PostgreSQL автоматически. Это займёт 2-3 минуты. После создания скопируй DATABASE_URL и добавь его во все функции.
                </p>
                {!API_ENDPOINTS.setupDatabase && (
                  <div className="bg-yellow-950/30 border border-yellow-500/30 rounded p-2 mb-3">
                    <p className="text-yellow-200 text-xs">
                      ⚠️ Сначала задеплой функцию <code className="bg-yellow-900/50 px-1 rounded">setup-database</code> через "Деплой backend-функций"
                    </p>
                  </div>
                )}
                {databaseSetupResult && (
                  <div className="bg-green-950/30 border border-green-500/30 rounded p-3 mb-3">
                    <p className="text-green-200 text-sm font-semibold mb-2">✅ БД создана!</p>
                    <div className="space-y-2 text-xs">
                      <div>
                        <p className="text-green-300 font-mono break-all">{databaseSetupResult.database_url}</p>
                        <Button
                          size="sm"
                          variant="outline"
                          className="mt-1 border-green-500/50 text-green-300 hover:bg-green-950/50"
                          onClick={() => {
                            navigator.clipboard.writeText(databaseSetupResult.database_url);
                            toast({ title: "Скопировано!", description: "DATABASE_URL скопирован" });
                          }}
                        >
                          <Icon name="Copy" className="h-3 w-3 mr-1" />
                          Копировать DATABASE_URL
                        </Button>
                      </div>
                      <p className="text-yellow-300">⚠️ Пароль: {databaseSetupResult.db_password} (сохрани его!)</p>
                    </div>
                  </div>
                )}
              </div>
              <Button
                onClick={handleSetupDatabase}
                disabled={isSettingUpDatabase}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white whitespace-nowrap"
              >
                {isSettingUpDatabase ? (
                  <>
                    <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                    Создаю БД...
                  </>
                ) : (
                  <>
                    <Icon name="Database" className="mr-2 h-4 w-4" />
                    Создать VM с БД
                  </>
                )}
              </Button>
            </div>
          </div>

          {/* Предупреждение о необходимости задеплоить функции деплойера */}
          {API_ENDPOINTS.deployFunctions?.includes('poehali.dev') && (
            <div className="mt-4 bg-orange-950/30 border border-orange-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <Icon name="AlertTriangle" className="h-5 w-5 text-orange-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm text-orange-200 text-left">
                  <p className="font-semibold mb-1">⚠️ Деплойер использует инфраструктуру poehali.dev</p>
                  <p className="text-xs mb-2">Чтобы перейти на свою инфраструктуру:</p>
                  <ol className="list-decimal list-inside space-y-1 text-xs">
                    <li><strong>Настрой БД:</strong> Создай Managed PostgreSQL в Yandex Cloud (см. SETUP_DEPLOYER_DATABASE.md)</li>
                    <li><strong>Задеплой функции:</strong> Добавь конфиг с репозиторием деплойера и нажми "Деплой backend-функций"</li>
                    <li><strong>Настрой секреты:</strong> Добавь DATABASE_URL во все функции (см. SETUP_DEPLOYER_DATABASE.md)</li>
                    <li><strong>Примени миграции:</strong> Нажми "Применить миграции БД"</li>
                    <li>После деплоя перезапусти dev сервер</li>
                  </ol>
                  <p className="text-xs mt-2 text-orange-300">
                    📖 Инструкции: DEPLOY_DEPLOYER_FUNCTIONS.md и SETUP_DEPLOYER_DATABASE.md
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        <Card className="bg-white/10 backdrop-blur border-white/20">
          <CardHeader>
            <div className="flex items-center justify-between">
              <CardTitle className="text-white flex items-center gap-2">
                <Icon name="Server" className="h-5 w-5 text-green-400" />
                Серверы
              </CardTitle>
              <div className="flex gap-2">
                <Button
                  onClick={handleSyncVMs}
                  disabled={isSyncing}
                  variant="outline"
                  className="border-blue-400/30 hover:bg-blue-400/10 text-blue-300"
                >
                  <Icon name={isSyncing ? "Loader2" : "RefreshCw"} className={`h-4 w-4 mr-2 ${isSyncing ? 'animate-spin' : ''}`} />
                  {isSyncing ? 'Синхронизация...' : 'Обновить'}
                </Button>
                <Button 
                  onClick={() => {
                    setNewVmName("");
                    setIsCreateVmDialogOpen(true);
                  }}
                  disabled={isCreatingVM}
                  className="bg-gradient-to-r from-green-500 to-emerald-600 hover:from-green-600 hover:to-emerald-700 text-white"
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
              <div className="text-center py-12 space-y-3">
                <Icon name="Server" className="h-12 w-12 text-slate-500 mx-auto" />
                <p className="text-slate-400">Нет активных серверов</p>
                <p className="text-slate-500 text-sm">Нажми "Создать VM" чтобы запустить новый сервер в Yandex Cloud</p>
              </div>
            ) : (
              <div className="grid gap-3">
                {vms.map(vm => {
                  const statusConfig = {
                    ready: { icon: 'CheckCircle', color: 'text-green-400', label: 'Готов' },
                    creating: { icon: 'Loader2', color: 'text-yellow-400', label: 'Создаётся...' },
                    stopped: { icon: 'XCircle', color: 'text-red-400', label: 'Остановлен' }
                  }[vm.status] || { icon: 'AlertCircle', color: 'text-gray-400', label: vm.status };

                  return (
                    <div key={vm.id} className="bg-slate-900/50 rounded-lg p-4 flex items-center justify-between">
                      <div className="flex items-center gap-4">
                        <Icon name={statusConfig.icon} className={`h-5 w-5 ${statusConfig.color} ${vm.status === 'creating' ? 'animate-spin' : ''}`} />
                        <div>
                          <div className="text-white font-semibold">{vm.name}</div>
                          <div className="text-slate-400 text-sm font-mono">{vm.ip_address || 'IP адрес ещё не назначен'}</div>
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className={`${statusConfig.color} text-sm`}>{statusConfig.label}</div>
                        <div className="flex items-center gap-2">
                          {vm.ip_address && (
                            <>
                              <Button
                                size="sm"
                                variant="outline"
                                className="border-blue-500/50 text-blue-300 hover:bg-blue-950/50"
                                onClick={() => handleGetSshKey(vm)}
                                disabled={isLoadingSshKey}
                              >
                                <Icon name="Key" className="h-3 w-3 mr-1" />
                                SSH ключ
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                className="border-amber-500/50 text-amber-300 hover:bg-amber-950/50"
                                onClick={() => setAddSshKeyDialog({ open: true, vm, keyValue: '' })}
                              >
                                <Icon name="Plus" className="h-3 w-3 mr-1" />
                                Добавить ключ
                              </Button>
                            </>
                          )}
                          <Button
                            size="sm"
                            variant="outline"
                            className="border-red-500/50 text-red-300 hover:bg-red-950/50"
                            onClick={() => setDeleteVmDialog({ open: true, vm })}
                            disabled={isDeletingVm}
                          >
                            <Icon name="Trash2" className="h-3 w-3 mr-1" />
                            Удалить
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
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
                    <p className="text-xs text-slate-400 mt-1">
                      💡 На одном сервере можно разместить несколько доменов. Домен настраивается автоматически в nginx.
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">GitHub репозиторий</Label>
                    <Input
                      value={newConfig.repo}
                      onChange={(e) => setNewConfig({...newConfig, repo: e.target.value})}
                      placeholder="username/repo или https://github.com/username/repo"
                      className="bg-slate-800 border-slate-700 text-white"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      💡 Можно указать как <code className="bg-slate-900 px-1 rounded">username/repo</code>, так и полный URL
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">GitHub токен</Label>
                    <Input
                      type="password"
                      value={newConfig.github_token}
                      onChange={(e) => {
                        const token = e.target.value;
                        setNewConfig({...newConfig, github_token: token});
                        // Сохраняем токен сразу при вводе (если имя конфига уже указано)
                        if (token.trim() && newConfig.name) {
                          try {
                            localStorage.setItem(`deploy_github_token_${newConfig.name}`, token);
                          } catch (e) {
                            console.error('Ошибка сохранения токена:', e);
                          }
                        }
                      }}
                      placeholder="ghp_... (для миграций и доступа к репо)"
                      className="bg-slate-800 border-slate-700 text-white"
                      autoComplete="off"
                    />
                    <p className="text-xs text-slate-400 mt-1">
                      Нужен для миграций БД. <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">Создать токен</a>
                      {newConfig.github_token ? ' ✅ Токен будет сохранён' : ''}
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">Сервер</Label>
                    <select
                      value={selectedVmId || ''}
                      onChange={(e) => setSelectedVmId(Number(e.target.value) || null)}
                      className="w-full bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2"
                    >
                      <option value="">Автоматически ({vms[0]?.name || 'нет серверов'})</option>
                      {vms.map(vm => (
                        <option key={vm.id} value={vm.id}>
                          {vm.name} ({vm.ip_address || 'создаётся...'})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <Label className="text-slate-300">Сервер с базой данных</Label>
                    <select
                      value={newConfig.database_vm_id || ''}
                      onChange={(e) => {
                        const vmId = Number(e.target.value) || 0;
                        const selectedVm = vms.find(vm => vm.id === vmId);
                        const dbUrl = selectedVm && selectedVm.ip_address 
                          ? `postgresql://deployer_user:ЗАМЕНИ_НА_ПАРОЛЬ@${selectedVm.ip_address}:5432/deployer`
                          : '';
                        setNewConfig({...newConfig, database_vm_id: vmId, database_url: dbUrl});
                      }}
                      className="w-full bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2"
                    >
                      <option value="">Не выбран (использовать БД из переменных окружения)</option>
                      {vms.map(vm => (
                        <option key={vm.id} value={vm.id}>
                          {vm.name} ({vm.ip_address || 'создаётся...'})
                        </option>
                      ))}
                    </select>
                    <p className="text-xs text-slate-400 mt-1">
                      💡 Выбери сервер с БД из списка выше. Если не выбран, миграции будут применяться к БД из переменных окружения функции migrate.
                    </p>
                  </div>
                  <div>
                    <Label className="text-slate-300">DATABASE_URL (автоматически или вручную)</Label>
                      <Input
                        value={newConfig.database_url || ''}
                        onChange={(e) => setNewConfig({...newConfig, database_url: e.target.value})}
                        placeholder="postgresql://user:pass@host:5432/db (заполнится автоматически при выборе сервера выше)"
                        className="bg-slate-800 border-slate-700 text-white"
                      />
                    <p className="text-xs text-slate-400 mt-1">
                      💡 Можно указать вручную или выбрать сервер выше для автоматического заполнения. Не забудь указать правильный пароль БД!
                    </p>
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
                    {editingConfig === config.name ? (
                      <div className="space-y-3">
                        <div>
                          <Label className="text-slate-300">Название</Label>
                          <Input
                            value={editConfig.name}
                            onChange={(e) => setEditConfig({...editConfig, name: e.target.value})}
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div>
                          <Label className="text-slate-300">Домен</Label>
                          <Input
                            value={editConfig.domain}
                            onChange={(e) => setEditConfig({...editConfig, domain: e.target.value})}
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div>
                          <Label className="text-slate-300">GitHub репозиторий</Label>
                          <Input
                            value={editConfig.repo}
                            onChange={(e) => setEditConfig({...editConfig, repo: e.target.value})}
                            placeholder="username/repo или https://github.com/username/repo"
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                        </div>
                        <div>
                          <Label className="text-slate-300">GitHub токен</Label>
                          <Input
                            type="password"
                            value={editConfig.github_token}
                            onChange={(e) => {
                              const token = e.target.value;
                              setEditConfig({...editConfig, github_token: token});
                              // Сохраняем токен сразу при вводе
                              if (token.trim()) {
                                try {
                                  const key = `deploy_github_token_${editConfig.name}`;
                                  localStorage.setItem(key, token);
                                  console.log(`Токен сохранён в localStorage под ключом: ${key}`);
                                } catch (e) {
                                  console.error('Ошибка сохранения токена:', e);
                                  toast({
                                    title: "Ошибка сохранения токена",
                                    description: "Не удалось сохранить токен в браузере. Проверь консоль.",
                                    variant: "destructive"
                                  });
                                }
                              }
                            }}
                            placeholder="ghp_... (для миграций)"
                            className="bg-slate-800 border-slate-700 text-white"
                            autoComplete="off"
                          />
                          <p className="text-xs text-slate-400 mt-1">
                            Сохраняется в браузере автоматически. Без токена кнопка «Миграции» не сработает.
                            {editConfig.github_token ? ' ✅ Токен сохранён' : ' ⚠️ Введи токен'}
                          </p>
                        </div>
                        <div>
                          <Label className="text-slate-300">Сервер</Label>
                          <select
                            value={editConfig.vmId || ''}
                            onChange={(e) => setEditConfig({...editConfig, vmId: Number(e.target.value) || 0})}
                            className="w-full bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2"
                          >
                            <option value="">Не выбран</option>
                            {vms.map(vm => (
                              <option key={vm.id} value={vm.id}>
                                {vm.name} ({vm.ip_address || 'создаётся...'})
                              </option>
                            ))}
                          </select>
                        </div>
                        <div>
                          <Label className="text-slate-300">Сервер с базой данных</Label>
                          <select
                            value={editConfig.database_vm_id || ''}
                            onChange={(e) => {
                              const vmId = Number(e.target.value) || 0;
                              const selectedVm = vms.find(vm => vm.id === vmId);
                              const dbUrl = selectedVm && selectedVm.ip_address 
                                ? `postgresql://deployer_user:ЗАМЕНИ_НА_ПАРОЛЬ@${selectedVm.ip_address}:5432/deployer`
                                : '';
                              setEditConfig({...editConfig, database_vm_id: vmId, database_url: dbUrl});
                            }}
                            className="w-full bg-slate-800 border border-slate-700 text-white rounded-md px-3 py-2"
                          >
                            <option value="">Не выбран (использовать БД из переменных окружения)</option>
                            {vms.map(vm => (
                              <option key={vm.id} value={vm.id}>
                                {vm.name} ({vm.ip_address || 'создаётся...'})
                              </option>
                            ))}
                          </select>
                          <p className="text-xs text-slate-400 mt-1">
                            💡 Выбери сервер с БД из списка выше. Если не выбран, миграции будут применяться к БД из переменных окружения функции migrate.
                          </p>
                        </div>
                        <div>
                          <Label className="text-slate-300">DATABASE_URL (автоматически или вручную)</Label>
                          <Input
                            value={editConfig.database_url}
                            onChange={(e) => setEditConfig({...editConfig, database_url: e.target.value})}
                            placeholder="postgresql://user:pass@host:5432/db (заполнится автоматически при выборе сервера выше)"
                            className="bg-slate-800 border-slate-700 text-white"
                          />
                          <p className="text-xs text-slate-400 mt-1">
                            💡 Можно указать вручную или выбрать сервер выше для автоматического заполнения. Не забудь указать правильный пароль БД!
                          </p>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <Button onClick={() => handleEditConfig(config.name)} className="bg-green-600 hover:bg-green-700">
                            <Icon name="Check" className="mr-2 h-4 w-4" />
                            Сохранить
                          </Button>
                          <Button onClick={() => setEditingConfig(null)} variant="outline" className="border-slate-600">
                            Отмена
                          </Button>
                          <Button
                            onClick={() => handleSetupSsl(config.name)}
                            disabled={isSettingUpSsl === config.name}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white"
                          >
                            {isSettingUpSsl === config.name ? (
                              <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Icon name="Lock" className="mr-2 h-4 w-4" />
                            )}
                            {isSettingUpSsl === config.name ? 'Устанавливаю SSL...' : 'Установить SSL'}
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <>
                        <div className="flex items-start justify-between mb-3">
                          <div className="flex-1">
                            <div className="text-white font-semibold text-lg mb-1">{config.domain}</div>
                            <div className="text-slate-400 text-sm mb-2">{config.github_repo}</div>
                            <div className="flex gap-4 text-xs text-slate-500">
                              <span>Конфиг: {config.name}</span>
                              {config.vm_ip && <span>IP: {config.vm_ip}</span>}
                            </div>
                          </div>
                          <div className="flex gap-1">
                            <Button
                              onClick={() => startEdit(config)}
                              size="sm"
                              variant="ghost"
                              className="text-blue-400 hover:text-blue-300 hover:bg-blue-950/50"
                            >
                              <Icon name="Edit" className="h-4 w-4" />
                            </Button>
                            <Button
                              onClick={() => handleDeleteConfig(config.name)}
                              size="sm"
                              variant="ghost"
                              className="text-red-400 hover:text-red-300 hover:bg-red-950/50"
                            >
                              <Icon name="Trash2" className="h-4 w-4" />
                            </Button>
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-2">
                          <Button
                            onClick={() => handleDeploy(config.name)}
                            disabled={isDeploying === config.name}
                            className="bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white font-semibold"
                          >
                            {isDeploying === config.name ? (
                              <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Icon name="Rocket" className="mr-2 h-4 w-4" />
                            )}
                            {isDeploying === config.name ? 'Деплою...' : 'Фронтенд'}
                          </Button>
                          <Button
                            onClick={() => handleSetupSsl(config.name)}
                            disabled={isSettingUpSsl === config.name}
                            className="bg-emerald-600 hover:bg-emerald-700 text-white font-semibold"
                          >
                            {isSettingUpSsl === config.name ? (
                              <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Icon name="Lock" className="mr-2 h-4 w-4" />
                            )}
                            {isSettingUpSsl === config.name ? 'SSL...' : 'SSL'}
                          </Button>
                          <Button
                            onClick={() => handleDeployFunctions(config)}
                            disabled={isDeployingFunctions === config.name}
                            className="bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-700 hover:to-indigo-700 text-white font-semibold"
                          >
                            {isDeployingFunctions === config.name ? (
                              <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Icon name="Cloud" className="mr-2 h-4 w-4" />
                            )}
                            {isDeployingFunctions === config.name ? 'Деплою...' : 'Backend'}
                          </Button>
                          <Button
                            onClick={() => handleMigrate(config)}
                            disabled={isMigrating === config.name}
                            className="bg-gradient-to-r from-orange-600 to-amber-600 hover:from-orange-700 hover:to-amber-700 text-white font-semibold"
                          >
                            {isMigrating === config.name ? (
                              <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                            ) : (
                              <Icon name="Database" className="mr-2 h-4 w-4" />
                            )}
                            {isMigrating === config.name ? 'Миграции...' : 'Миграции'}
                          </Button>
                        </div>
                      </>
                    )}
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Диалог SSH ключа */}
        <Dialog open={sshKeyDialog.open} onOpenChange={(open) => setSshKeyDialog({ open, vm: null, sshKey: null })}>
          <DialogContent className="max-w-2xl bg-slate-900 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-white flex items-center gap-2">
                <Icon name="Key" className="h-5 w-5 text-blue-400" />
                SSH ключ для {sshKeyDialog.vm?.name}
              </DialogTitle>
              <DialogDescription className="text-slate-300">
                Используй этот приватный ключ для подключения к серверу
              </DialogDescription>
            </DialogHeader>
            
            {sshKeyDialog.sshKey && sshKeyDialog.vm && (
              <div className="space-y-4">
                <div className="bg-slate-950 rounded-lg p-4 border border-slate-700">
                  <div className="flex items-center justify-between mb-2">
                    <Label className="text-slate-300 text-sm">Приватный ключ:</Label>
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-blue-500/50 text-blue-300 hover:bg-blue-950/50"
                      onClick={() => {
                        navigator.clipboard.writeText(sshKeyDialog.sshKey || '');
                        toast({
                          title: "Скопировано!",
                          description: "SSH ключ скопирован в буфер обмена",
                        });
                      }}
                    >
                      <Icon name="Copy" className="h-3 w-3 mr-1" />
                      Копировать
                    </Button>
                  </div>
                  <pre className="text-xs text-slate-300 bg-slate-900 p-3 rounded overflow-x-auto font-mono">
                    {sshKeyDialog.sshKey}
                  </pre>
                </div>

                <div className="bg-blue-950/30 border border-blue-500/30 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Icon name="Info" className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-blue-200 space-y-2">
                      <p className="font-semibold">Как использовать:</p>
                      <ol className="list-decimal list-inside space-y-1 text-xs">
                        <li>Сохрани ключ в файл: <code className="bg-slate-900 px-1 rounded">~/.ssh/{sshKeyDialog.vm.name}_key</code></li>
                        <li>Установи права: <code className="bg-slate-900 px-1 rounded">chmod 600 ~/.ssh/{sshKeyDialog.vm.name}_key</code></li>
                        <li>Подключись: <code className="bg-slate-900 px-1 rounded">ssh -i ~/.ssh/{sshKeyDialog.vm.name}_key {sshKeyDialog.vm.ssh_user}@{sshKeyDialog.vm.ip_address}</code></li>
                      </ol>
                    </div>
                  </div>
                </div>

                <div className="bg-yellow-950/30 border border-yellow-500/30 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Icon name="AlertTriangle" className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-yellow-200">
                      <p className="font-semibold mb-1">Важно:</p>
                      <p className="text-xs">Сохрани этот ключ в безопасном месте! Без него ты не сможешь подключиться к серверу.</p>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={() => {
                      const blob = new Blob([sshKeyDialog.sshKey || ''], { type: 'text/plain' });
                      const url = URL.createObjectURL(blob);
                      const a = document.createElement('a');
                      a.href = url;
                      a.download = `${sshKeyDialog.vm?.name}_key.pem`;
                      document.body.appendChild(a);
                      a.click();
                      document.body.removeChild(a);
                      URL.revokeObjectURL(url);
                      toast({
                        title: "Скачано!",
                        description: "SSH ключ сохранён в файл",
                      });
                    }}
                    className="flex-1 bg-gradient-to-r from-green-600 to-blue-600 hover:from-green-700 hover:to-blue-700 text-white"
                  >
                    <Icon name="Download" className="mr-2 h-4 w-4" />
                    Скачать ключ
                  </Button>
                  <Button
                    onClick={() => setSshKeyDialog({ open: false, vm: null, sshKey: null })}
                    variant="outline"
                    className="border-slate-600 text-slate-300"
                  >
                    Закрыть
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Диалог добавления SSH ключа */}
        <Dialog open={addSshKeyDialog.open} onOpenChange={(open) => !isSavingSshKey && setAddSshKeyDialog({ open, vm: null, keyValue: '' })}>
          <DialogContent className="max-w-2xl bg-slate-900 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-white flex items-center gap-2">
                <Icon name="Key" className="h-5 w-5 text-amber-400" />
                Добавить SSH ключ для {addSshKeyDialog.vm?.name}
              </DialogTitle>
              <DialogDescription className="text-slate-300">
                Вставь приватный ключ — он будет сохранён в БД, деплой заработает
              </DialogDescription>
            </DialogHeader>
            {addSshKeyDialog.vm && (
              <div className="space-y-4">
                <div>
                  <Label className="text-slate-300">Приватный SSH ключ</Label>
                  <Textarea
                    placeholder="-----BEGIN OPENSSH PRIVATE KEY-----
...
-----END OPENSSH PRIVATE KEY-----"
                    value={addSshKeyDialog.keyValue}
                    onChange={(e) => setAddSshKeyDialog({ ...addSshKeyDialog, keyValue: e.target.value })}
                    className="bg-slate-800 border-slate-700 text-white font-mono text-sm min-h-[180px] mt-2"
                  />
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handleSaveSshKeyToDb}
                    disabled={isSavingSshKey || !addSshKeyDialog.keyValue.trim()}
                    className="bg-amber-600 hover:bg-amber-700"
                  >
                    {isSavingSshKey ? 'Сохранение...' : 'Сохранить в БД'}
                  </Button>
                  <Button variant="outline" className="border-slate-600" onClick={() => setAddSshKeyDialog({ open: false, vm: null, keyValue: '' })} disabled={isSavingSshKey}>
                    Отмена
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Диалог подтверждения удаления VM */}
        <Dialog open={deleteVmDialog.open} onOpenChange={(open) => setDeleteVmDialog({ open, vm: null })}>
          <DialogContent className="max-w-md bg-slate-900 border-slate-700">
            <DialogHeader>
              <DialogTitle className="text-white flex items-center gap-2">
                <Icon name="AlertTriangle" className="h-5 w-5 text-red-400" />
                Удалить VM?
              </DialogTitle>
              <DialogDescription className="text-slate-300">
                Это действие нельзя отменить
              </DialogDescription>
            </DialogHeader>
            
            {deleteVmDialog.vm && (
              <div className="space-y-4">
                <div className="bg-slate-950 rounded-lg p-4 border border-slate-700">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Название:</span>
                      <span className="text-white font-semibold">{deleteVmDialog.vm.name}</span>
                    </div>
                    {deleteVmDialog.vm.ip_address && (
                      <div className="flex justify-between">
                        <span className="text-slate-400">IP адрес:</span>
                        <span className="text-white font-mono">{deleteVmDialog.vm.ip_address}</span>
                      </div>
                    )}
                    <div className="flex justify-between">
                      <span className="text-slate-400">Статус:</span>
                      <span className="text-white">{deleteVmDialog.vm.status}</span>
                    </div>
                  </div>
                </div>

                {(() => {
                  const linkedConfigs = configs.filter(c => c.vm_instance_id === deleteVmDialog.vm?.id);
                  return linkedConfigs.length > 0 ? (
                    <div className="bg-orange-950/30 border border-orange-500/30 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <Icon name="AlertCircle" className="h-5 w-5 text-orange-400 flex-shrink-0 mt-0.5" />
                        <div className="text-sm text-orange-200">
                          <p className="font-semibold mb-1">К этой VM привязаны конфиги:</p>
                          <ul className="list-disc list-inside space-y-1 text-xs">
                            {linkedConfigs.map(c => (
                              <li key={c.id} className="font-mono">{c.name}</li>
                            ))}
                          </ul>
                          <p className="text-xs mt-2 text-orange-300">Они перестанут работать после удаления VM</p>
                        </div>
                      </div>
                    </div>
                  ) : null;
                })()}

                <div className="bg-red-950/30 border border-red-500/30 rounded-lg p-4">
                  <div className="flex items-start gap-3">
                    <Icon name="AlertTriangle" className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
                    <div className="text-sm text-red-200">
                      <p className="font-semibold mb-1">Внимание!</p>
                      <ul className="list-disc list-inside space-y-1 text-xs">
                        <li>VM будет удалена из Yandex Cloud</li>
                        <li>Все данные на сервере будут потеряны</li>
                        <li>Это действие нельзя отменить</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <div className="flex gap-2">
                  <Button
                    onClick={handleDeleteVm}
                    disabled={isDeletingVm}
                    className="flex-1 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 text-white"
                  >
                    {isDeletingVm ? (
                      <>
                        <Icon name="Loader2" className="mr-2 h-4 w-4 animate-spin" />
                        Удаляю...
                      </>
                    ) : (
                      <>
                        <Icon name="Trash2" className="mr-2 h-4 w-4" />
                        Удалить VM
                      </>
                    )}
                  </Button>
                  <Button
                    onClick={() => setDeleteVmDialog({ open: false, vm: null })}
                    variant="outline"
                    className="border-slate-600 text-slate-300"
                    disabled={isDeletingVm}
                  >
                    Отмена
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>
      </div>
    </div>
  );
}
