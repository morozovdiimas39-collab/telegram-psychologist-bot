import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import Icon from "@/components/ui/icon";

const Index = () => {


  const cases = [
    {
      category: "E-commerce",
      title: "Интернет-магазин электроники",
      metrics: [
        { label: "Рост продаж", value: "+340%" },
        { label: "Стоимость заявки", value: "-65%" },
        { label: "ROI", value: "520%" }
      ]
    },
    {
      category: "Услуги",
      title: "Сеть стоматологических клиник",
      metrics: [
        { label: "Записей на прием", value: "+280%" },
        { label: "Стоимость клика", value: "-48%" },
        { label: "Конверсия", value: "12.4%" }
      ]
    },
    {
      category: "B2B",
      title: "Производство промышленного оборудования",
      metrics: [
        { label: "Заявок в месяц", value: "+150%" },
        { label: "CPL", value: "1200₽" },
        { label: "Качество лидов", value: "94%" }
      ]
    }
  ];

  const stats = [
    { value: "150+", label: "Успешных проектов" },
    { value: "5 лет", label: "На рынке" },
    { value: "₽450M+", label: "Бюджет под управлением" },
    { value: "98%", label: "Клиентов остаются с нами" }
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-blue-50 via-background to-indigo-50">
        <div className="container mx-auto px-4 py-20 md:py-32">
          <div className="max-w-3xl mx-auto text-center space-y-8">
            <Badge variant="secondary" className="text-sm px-4 py-2">
              Директолог с опытом 5+ лет
            </Badge>
            <h1 className="text-4xl md:text-6xl font-bold tracking-tight">
              Привлекаю клиентов из контекстной рекламы
            </h1>
            <p className="text-xl text-muted-foreground">
              Настраиваю и веду рекламные кампании в Яндекс.Директ и Google Ads.
              Работаю на результат — вы платите только за реальные заявки и продажи.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" className="text-lg h-14 px-8">
                <Icon name="MessageCircle" className="mr-2 h-5 w-5" />
                Обсудить проект
              </Button>
              <Button size="lg" variant="outline" className="text-lg h-14 px-8">
                <Icon name="FileText" className="mr-2 h-5 w-5" />
                Смотреть кейсы
              </Button>
            </div>
          </div>
        </div>
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <div className="absolute top-1/2 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl" />
          <div className="absolute bottom-0 right-1/4 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl" />
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 border-y bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center space-y-2">
                <div className="text-4xl md:text-5xl font-bold text-primary">
                  {stat.value}
                </div>
                <div className="text-sm text-muted-foreground">
                  {stat.label}
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>



      {/* Cases Section */}
      <section className="py-20 bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4 mb-16">
            <h2 className="text-3xl md:text-4xl font-bold">Кейсы</h2>
            <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
              Реальные результаты работы с клиентами из разных ниш
            </p>
          </div>
          <div className="grid md:grid-cols-3 gap-8">
            {cases.map((caseItem, index) => (
              <Card key={index} className="overflow-hidden hover:shadow-lg transition-shadow">
                <div className="h-2 bg-primary" />
                <CardContent className="pt-6 pb-8 space-y-6">
                  <div>
                    <Badge variant="secondary" className="mb-3">
                      {caseItem.category}
                    </Badge>
                    <h3 className="text-xl font-semibold">{caseItem.title}</h3>
                  </div>
                  <div className="space-y-4">
                    {caseItem.metrics.map((metric, idx) => (
                      <div key={idx} className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground">
                          {metric.label}
                        </span>
                        <span className="text-lg font-bold text-primary">
                          {metric.value}
                        </span>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <Card className="border-2 bg-gradient-to-br from-primary/5 to-accent/5">
            <CardContent className="py-16 px-8 text-center space-y-6">
              <h2 className="text-3xl md:text-4xl font-bold">
                Готовы увеличить продажи?
              </h2>
              <p className="text-lg text-muted-foreground max-w-2xl mx-auto">
                Получите бесплатный аудит текущей рекламы и персональную стратегию развития
              </p>
              <div className="flex flex-col sm:flex-row gap-4 justify-center pt-4">
                <Button size="lg" className="text-lg h-14 px-8">
                  <Icon name="Calendar" className="mr-2 h-5 w-5" />
                  Записаться на консультацию
                </Button>
                <Button size="lg" variant="outline" className="text-lg h-14 px-8">
                  <Icon name="Send" className="mr-2 h-5 w-5" />
                  Telegram
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t bg-muted/30">
        <div className="container mx-auto px-4">
          <div className="grid md:grid-cols-3 gap-8">
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Контакты</h3>
              <div className="space-y-2 text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Icon name="Mail" className="h-4 w-4" />
                  <span>hello@directolog.ru</span>
                </div>
                <div className="flex items-center gap-2">
                  <Icon name="Phone" className="h-4 w-4" />
                  <span>+7 (999) 123-45-67</span>
                </div>
              </div>
            </div>
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Работаю с</h3>
              <div className="flex flex-wrap gap-2">
                <Badge variant="outline">Яндекс.Директ</Badge>
                <Badge variant="outline">Google Ads</Badge>
                <Badge variant="outline">Метрика</Badge>
                <Badge variant="outline">Analytics</Badge>
              </div>
            </div>
            <div className="space-y-4">
              <h3 className="font-semibold text-lg">Соцсети</h3>
              <div className="flex gap-3">
                <Button variant="outline" size="icon">
                  <Icon name="Send" className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon">
                  <Icon name="Instagram" className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="icon">
                  <Icon name="Linkedin" className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </div>
          <div className="mt-12 pt-8 border-t text-center text-sm text-muted-foreground">
            © 2026 Директолог. Все права защищены.
          </div>
        </div>
      </footer>
    </div>
  );
};

export default Index;