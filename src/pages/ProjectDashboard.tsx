import React, { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import Icon from "@/components/ui/icon";
import { ScrollArea } from "@/components/ui/scroll-area";
import { API_ENDPOINTS } from "@/lib/api";
import { toast } from "sonner";

interface CloudResource {
  type: string;
  count: number;
  active: number;
}

interface Project {
  id: string;
  name: string;
  status: "running" | "stopped" | "error";
  region: string;
  resources: {
    cpu: string;
    ram: string;
    disk: string;
    vms: number;
    functions: number;
  };
  network: {
    inbound: string;
    outbound: string;
    uptime: string;
  };
}

const ProjectDashboard = () => {
  const [projects, setProjects] = useState<Project[]>([
    {
      id: "1",
      name: "prod-psychologist-bot",
      status: "running",
      region: "ru-central1-a",
      resources: { cpu: "12%", ram: "456MB / 2GB", disk: "12.4GB / 32GB", vms: 1, functions: 4 },
      network: { inbound: "45 Kbps", outbound: "12 Kbps", uptime: "14д 6ч 12м" }
    }
  ]);
  const [selectedId, setSelectedId] = useState("1");
  const [isLoading, setIsLoading] = useState(false);

  // Фетч реальных данных из Яндекс Облака
  const fetchCloudData = async () => {
    if (!API_ENDPOINTS.projectApi) {
      console.warn("Project API URL not found. Please deploy backend/project-api first.");
      return;
    }

    setIsLoading(true);
    try {
      const response = await fetch(API_ENDPOINTS.projectApi);
      if (!response.ok) throw new Error("Ошибка при запросе к API");
      
      const data = await response.json();
      
      // Обновляем данные проекта на основе ответа API
      // В реальном сценарии мы бы получили массив проектов из БД
      // Но пока обновляем наш моковый проект реальными цифрами из облака
      setProjects(prev => prev.map(p => {
        if (p.id === "1") {
          return {
            ...p,
            resources: {
              ...p.resources,
              vms: data.resources?.vms?.count || 0,
              functions: data.resources?.functions?.count || 0
            }
          };
        }
        return p;
      }));

      toast.success("Данные обновлены");
    } catch (error) {
      console.error("Fetch error:", error);
      toast.error("Не удалось получить данные из облака");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchCloudData();
    // Автообновление каждые 30 секунд
    const interval = setInterval(fetchCloudData, 30000);
    return () => clearInterval(interval);
  }, []);

  const currentProject = projects.find(p => p.id === selectedId) || projects[0];

  return (
    <div className="flex h-screen bg-[#020617] text-slate-300 font-mono antialiased overflow-hidden">
      
      {/* САЙДБАР */}
      <aside className="w-72 bg-[#0F172A] border-r border-slate-800 flex flex-col">
        <div className="p-6 border-b border-slate-800 flex items-center gap-3">
          <div className="h-7 w-7 bg-blue-600 rounded flex items-center justify-center">
            <Icon name="Server" className="text-white h-4 w-4" />
          </div>
          <span className="font-bold text-sm tracking-tight text-white uppercase tracking-tighter">Консоль хостинга</span>
        </div>

        <div className="p-4 space-y-4">
          <div className="px-2">
             <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-4">Ваши инстансы</p>
             <ScrollArea className="h-[calc(100vh-140px)]">
                <div className="space-y-1">
                  {projects.map((project) => (
                    <button
                      key={project.id}
                      onClick={() => setSelectedId(project.id)}
                      className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors text-left ${
                        selectedId === project.id 
                        ? "bg-blue-600/10 text-blue-400 ring-1 ring-blue-500/20" 
                        : "text-slate-500 hover:bg-slate-800/50 hover:text-slate-300"
                      }`}
                    >
                      <div className={`h-1.5 w-1.5 rounded-full ${
                        project.status === 'running' ? 'bg-emerald-500' : 'bg-rose-500'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <p className="font-bold text-xs truncate">{project.name}</p>
                      </div>
                    </button>
                  ))}
                </div>
             </ScrollArea>
          </div>
        </div>
      </aside>

      {/* РАБОЧАЯ ОБЛАСТЬ */}
      <main className="flex-1 overflow-y-auto bg-[#020617]">
        {/* Шапка */}
        <header className="sticky top-0 z-10 bg-[#020617]/90 backdrop-blur-md border-b border-slate-800 px-8 py-4 flex items-center justify-between">
           <div className="flex items-center gap-4">
              <h2 className="font-bold text-sm text-white uppercase tracking-widest">{currentProject.name}</h2>
              <Badge variant="outline" className={`text-[10px] uppercase border-slate-700 ${
                currentProject.status === 'running' ? 'text-emerald-400 bg-emerald-400/5' : 'text-rose-400 bg-rose-400/5'
              }`}>
                {currentProject.status === 'running' ? 'Активен' : 'Ошибка'}
              </Badge>
              {isLoading && <Icon name="RefreshCw" className="h-3 w-3 animate-spin text-blue-500" />}
           </div>
           <div className="flex gap-2">
              <Button 
                size="sm" 
                variant="outline" 
                className="border-slate-800 bg-slate-900 text-xs font-bold text-slate-400 hover:text-white"
                onClick={fetchCloudData}
              >
                Обновить данные
              </Button>
              <Button size="sm" className="bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold px-4">
                Собрать билд
              </Button>
           </div>
        </header>

        <div className="p-8 space-y-8 max-w-7xl">
          
          {/* Технические метрики */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
             <Card className="bg-[#0F172A] border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                <CardHeader className="pb-2">
                   <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Загрузка CPU</p>
                </CardHeader>
                <CardContent className="space-y-4">
                   <div className="flex justify-between items-end">
                      <span className="text-3xl font-bold text-white tracking-tighter">{currentProject.resources.cpu}</span>
                      <span className="text-[10px] text-slate-500 font-bold">2 Ядра v3</span>
                   </div>
                   <Progress value={parseInt(currentProject.resources.cpu)} className="h-1 bg-slate-800" />
                </CardContent>
             </Card>

             <Card className="bg-[#0F172A] border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                <CardHeader className="pb-2">
                   <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Оперативная память</p>
                </CardHeader>
                <CardContent className="space-y-4">
                   <div className="flex justify-between items-end">
                      <span className="text-3xl font-bold text-white tracking-tighter">{currentProject.resources.ram.split(' / ')[0]}</span>
                      <span className="text-[10px] text-slate-500 font-bold">Лимит: {currentProject.resources.ram.split(' / ')[1]}</span>
                   </div>
                   <Progress value={25} className="h-1 bg-slate-800" />
                </CardContent>
             </Card>

             <Card className="bg-[#0F172A] border-slate-800 rounded-xl overflow-hidden shadow-2xl">
                <CardHeader className="pb-2">
                   <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500">Дисковое пространство</p>
                </CardHeader>
                <CardContent className="space-y-4">
                   <div className="flex justify-between items-end">
                      <span className="text-3xl font-bold text-white tracking-tighter">{currentProject.resources.disk.split(' / ')[0]}</span>
                      <span className="text-[10px] text-slate-500 font-bold">SSD: {currentProject.resources.disk.split(' / ')[1]}</span>
                   </div>
                   <Progress value={40} className="h-1 bg-slate-800" />
                </CardContent>
             </Card>
          </div>

          {/* Сеть и аптайм */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
             <Card className="bg-[#0F172A] border-slate-800 rounded-xl">
                <CardHeader className="border-b border-slate-800 py-4">
                   <h3 className="text-xs font-bold uppercase tracking-widest text-white">Трафик и доступность</h3>
                </CardHeader>
                <CardContent className="p-6">
                   <div className="grid grid-cols-2 gap-8">
                      <div className="space-y-2">
                         <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-black">
                            <Icon name="ArrowDown" className="h-3 w-3 text-emerald-500" /> Входящий
                         </div>
                         <p className="text-xl font-bold text-white tracking-tighter">{currentProject.network.inbound}</p>
                      </div>
                      <div className="space-y-2">
                         <div className="flex items-center gap-2 text-[10px] text-slate-500 uppercase font-black">
                            <Icon name="ArrowUp" className="h-3 w-3 text-blue-500" /> Исходящий
                         </div>
                         <p className="text-xl font-bold text-white tracking-tighter">{currentProject.network.outbound}</p>
                      </div>
                   </div>
                   <div className="mt-8 pt-8 border-t border-slate-800/50 flex justify-between items-center">
                      <span className="text-xs text-slate-500 font-bold uppercase">Uptime:</span>
                      <span className="text-xs font-black text-emerald-400">{currentProject.network.uptime}</span>
                   </div>
                </CardContent>
             </Card>

             <Card className="bg-[#0F172A] border-slate-800 rounded-xl overflow-hidden flex flex-col">
                <CardHeader className="border-b border-slate-800 py-4">
                   <h3 className="text-xs font-bold uppercase tracking-widest text-white">Технические события</h3>
                </CardHeader>
                <CardContent className="p-0 flex-1">
                   <div className="divide-y divide-slate-800/30">
                      {[
                        { event: "Бэкап успешно завершен", time: "12 мин. назад", status: "ok" },
                        { event: "Проверка здоровья: ru-central1-a", time: "1 ч. назад", status: "ok" },
                        { event: "Деплой билда #452", time: "4 ч. назад", status: "ok" },
                        { event: "Предупреждение по памяти", time: "Вчера", status: "warn" }
                      ].map((item, idx) => (
                        <div key={idx} className="px-6 py-3 flex items-center justify-between text-[10px]">
                           <div className="flex items-center gap-3">
                              <div className={`h-1 w-1 rounded-full ${item.status === 'ok' ? 'bg-emerald-500' : 'bg-amber-500'}`} />
                              <span className="text-slate-400 font-bold">{item.event}</span>
                           </div>
                           <span className="text-slate-600 font-black">{item.time}</span>
                        </div>
                      ))}
                   </div>
                   <div className="p-4 bg-slate-900/30 text-center border-t border-slate-800">
                      <button className="text-[10px] font-bold text-blue-500 uppercase hover:text-blue-400 tracking-tighter">Все логи системы</button>
                   </div>
                </CardContent>
             </Card>
          </div>

          {/* Инфраструктурный обзор */}
          <section className="bg-[#0F172A] rounded-xl border border-slate-800 p-8 space-y-6">
             <div className="flex items-center justify-between border-b border-slate-800 pb-4">
                <h3 className="text-xs font-bold uppercase tracking-widest text-white">Ресурсы Яндекс Облака</h3>
                <span className="text-[10px] text-slate-500 uppercase font-black">Регион: {currentProject.region}</span>
             </div>
             
             <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-lg text-center group hover:border-indigo-500/30 transition-all">
                   <Icon name="Server" className="h-5 w-5 text-indigo-400 mx-auto mb-2 group-hover:scale-110 transition-transform" />
                   <p className="text-[10px] text-slate-500 uppercase mb-1 font-bold">Инстансы VM</p>
                   <p className="text-2xl font-black text-white tracking-tighter">{currentProject.resources.vms}</p>
                </div>
                <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-lg text-center group hover:border-amber-500/30 transition-all">
                   <Icon name="Zap" className="h-5 w-5 text-amber-400 mx-auto mb-2 group-hover:scale-110 transition-transform" />
                   <p className="text-[10px] text-slate-500 uppercase mb-1 font-bold">Функции</p>
                   <p className="text-2xl font-black text-white tracking-tighter">{currentProject.resources.functions}</p>
                </div>
                <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-lg text-center group hover:border-rose-500/30 transition-all">
                   <Icon name="Database" className="h-5 w-5 text-rose-400 mx-auto mb-2 group-hover:scale-110 transition-transform" />
                   <p className="text-[10px] text-slate-500 uppercase mb-1 font-bold">База данных</p>
                   <p className="text-[11px] font-black text-white mt-1">PostgreSQL 15</p>
                </div>
                <div className="p-4 bg-slate-900/50 border border-slate-800 rounded-lg text-center group hover:border-emerald-500/30 transition-all">
                   <Icon name="Shield" className="h-5 w-5 text-emerald-400 mx-auto mb-2 group-hover:scale-110 transition-transform" />
                   <p className="text-[10px] text-slate-500 uppercase mb-1 font-bold">Защита</p>
                   <p className="text-[11px] font-black text-white mt-1">SSL Активен</p>
                </div>
             </div>
          </section>

        </div>
      </main>
    </div>
  );
};

export default ProjectDashboard;
