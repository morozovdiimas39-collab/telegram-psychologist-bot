import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import Icon from '@/components/ui/icon';
import { toast } from 'sonner';

export default function RealtyLeads() {
  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    propertyType: '',
    budget: '',
    comment: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    toast.success('Заявка отправлена! Мы свяжемся с вами в ближайшее время.');
    setFormData({ name: '', phone: '', propertyType: '', budget: '', comment: '' });
  };

  const benefits = [
    {
      icon: 'Users',
      title: 'Горячие лиды',
      description: 'Только проверенные клиенты, готовые к покупке недвижимости в Ставрополе'
    },
    {
      icon: 'TrendingUp',
      title: 'Высокая конверсия',
      description: 'Конверсия в сделку до 35% благодаря качественной предварительной работе'
    },
    {
      icon: 'Shield',
      title: 'Гарантия качества',
      description: 'Возврат средств, если лид не соответствует заявленным параметрам'
    },
    {
      icon: 'Clock',
      title: 'Быстрая передача',
      description: 'Получайте контакты клиентов в течение 1 часа после оплаты'
    }
  ];

  const stats = [
    { value: '500+', label: 'Успешных сделок' },
    { value: '150+', label: 'Довольных агентов' },
    { value: '35%', label: 'Средняя конверсия' },
    { value: '24/7', label: 'Поддержка клиентов' }
  ];

  const propertyTypes = [
    { icon: 'Building2', name: 'Квартиры', desc: 'Новостройки и вторичка' },
    { icon: 'Home', name: 'Дома', desc: 'Загородная недвижимость' },
    { icon: 'Warehouse', name: 'Коммерция', desc: 'Офисы и помещения' },
    { icon: 'Landmark', name: 'Элитное жильё', desc: 'Premium сегмент' }
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950 to-slate-950">
      {/* Hero Section */}
      <section className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-600/20 to-transparent" />
        <div className="container mx-auto px-4 py-20 relative">
          <div className="max-w-4xl mx-auto text-center space-y-8">
            <div className="inline-block">
              <span className="bg-blue-600/20 text-blue-300 px-4 py-2 rounded-full text-sm font-medium border border-blue-500/30">
                #1 платформа лидов в Ставрополе
              </span>
            </div>
            
            <h1 className="text-5xl md:text-7xl font-bold text-white leading-tight">
              Готовые клиенты
              <span className="block bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                на покупку недвижимости
              </span>
            </h1>
            
            <p className="text-xl md:text-2xl text-slate-300 max-w-2xl mx-auto">
              Продаём проверенные лиды агентствам и риелторам Ставрополя. 
              Платите только за результат.
            </p>

            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Button 
                size="lg" 
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-lg px-8 py-6"
                onClick={() => document.getElementById('order-form')?.scrollIntoView({ behavior: 'smooth' })}
              >
                <Icon name="Rocket" size={24} className="mr-2" />
                Получить лиды
              </Button>
              <Button 
                size="lg" 
                variant="outline" 
                className="border-white/20 text-white hover:bg-white/10 text-lg px-8 py-6"
                onClick={() => document.getElementById('benefits')?.scrollIntoView({ behavior: 'smooth' })}
              >
                Узнать больше
                <Icon name="ChevronDown" size={24} className="ml-2" />
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 bg-black/30 backdrop-blur">
        <div className="container mx-auto px-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-4xl md:text-5xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent mb-2">
                  {stat.value}
                </div>
                <div className="text-slate-400">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits Section */}
      <section id="benefits" className="py-20">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
              Почему выбирают нас
            </h2>
            <p className="text-xl text-slate-400">
              Работаем только с качественными лидами
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {benefits.map((benefit, i) => (
              <Card key={i} className="bg-white/5 backdrop-blur border-white/10 hover:bg-white/10 transition-all duration-300 hover:scale-105">
                <CardContent className="p-6 space-y-4">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-blue-600 to-purple-600 flex items-center justify-center">
                    <Icon name={benefit.icon as any} size={28} className="text-white" />
                  </div>
                  <h3 className="text-xl font-bold text-white">{benefit.title}</h3>
                  <p className="text-slate-400">{benefit.description}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Property Types */}
      <section className="py-20 bg-black/30 backdrop-blur">
        <div className="container mx-auto px-4">
          <div className="text-center mb-16">
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
              Типы недвижимости
            </h2>
            <p className="text-xl text-slate-400">
              Лиды по всем сегментам рынка
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {propertyTypes.map((type, i) => (
              <Card key={i} className="bg-gradient-to-br from-white/5 to-white/0 backdrop-blur border-white/10 hover:border-blue-500/50 transition-all duration-300 cursor-pointer group">
                <CardContent className="p-6 text-center space-y-4">
                  <div className="w-16 h-16 rounded-full bg-blue-600/20 flex items-center justify-center mx-auto group-hover:scale-110 transition-transform">
                    <Icon name={type.icon as any} size={32} className="text-blue-400" />
                  </div>
                  <h3 className="text-xl font-bold text-white">{type.name}</h3>
                  <p className="text-slate-400">{type.desc}</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section className="py-20">
        <div className="container mx-auto px-4">
          <div className="max-w-4xl mx-auto">
            <div className="text-center mb-16">
              <h2 className="text-4xl md:text-5xl font-bold text-white mb-4">
                Прозрачное ценообразование
              </h2>
              <p className="text-xl text-slate-400">
                Платите только за качество
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
              {[
                { name: 'Базовый', price: '2 500', leads: '5', desc: 'Для начинающих' },
                { name: 'Профи', price: '8 000', leads: '25', desc: 'Популярный выбор', popular: true },
                { name: 'Бизнес', price: '20 000', leads: '75', desc: 'Для агентств' }
              ].map((plan, i) => (
                <Card key={i} className={`relative ${plan.popular ? 'bg-gradient-to-br from-blue-600/20 to-purple-600/20 border-blue-500/50 scale-105' : 'bg-white/5 border-white/10'} backdrop-blur`}>
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2">
                      <span className="bg-gradient-to-r from-blue-600 to-purple-600 text-white px-4 py-1 rounded-full text-sm font-bold">
                        Хит продаж
                      </span>
                    </div>
                  )}
                  <CardContent className="p-6 space-y-6">
                    <div className="text-center">
                      <h3 className="text-xl font-bold text-white mb-2">{plan.name}</h3>
                      <p className="text-slate-400 text-sm">{plan.desc}</p>
                    </div>
                    <div className="text-center">
                      <div className="text-5xl font-bold text-white">{plan.price}₽</div>
                      <div className="text-slate-400 mt-2">{plan.leads} лидов</div>
                    </div>
                    <Button 
                      className={`w-full ${plan.popular ? 'bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700' : 'bg-white/10 hover:bg-white/20'}`}
                      onClick={() => document.getElementById('order-form')?.scrollIntoView({ behavior: 'smooth' })}
                    >
                      Заказать
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Order Form */}
      <section id="order-form" className="py-20 bg-black/30 backdrop-blur">
        <div className="container mx-auto px-4">
          <div className="max-w-2xl mx-auto">
            <Card className="bg-white/5 backdrop-blur border-white/10">
              <CardContent className="p-8">
                <div className="text-center mb-8">
                  <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
                    Начните получать клиентов
                  </h2>
                  <p className="text-slate-400">
                    Заполните форму, и мы свяжемся с вами в течение 15 минут
                  </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                  <div>
                    <label className="text-white font-medium mb-2 block">Ваше имя</label>
                    <Input
                      placeholder="Иван Иванов"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      required
                      className="bg-white/10 border-white/20 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div>
                    <label className="text-white font-medium mb-2 block">Телефон</label>
                    <Input
                      type="tel"
                      placeholder="+7 (999) 123-45-67"
                      value={formData.phone}
                      onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                      required
                      className="bg-white/10 border-white/20 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div>
                    <label className="text-white font-medium mb-2 block">Тип недвижимости</label>
                    <select
                      value={formData.propertyType}
                      onChange={(e) => setFormData({ ...formData, propertyType: e.target.value })}
                      required
                      className="w-full bg-white/10 border border-white/20 text-white rounded-md px-3 py-2"
                    >
                      <option value="">Выберите тип</option>
                      <option value="apartments">Квартиры</option>
                      <option value="houses">Дома</option>
                      <option value="commercial">Коммерция</option>
                      <option value="elite">Элитное жильё</option>
                      <option value="all">Все типы</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-white font-medium mb-2 block">Бюджет на лиды (₽)</label>
                    <Input
                      type="number"
                      placeholder="10000"
                      value={formData.budget}
                      onChange={(e) => setFormData({ ...formData, budget: e.target.value })}
                      required
                      className="bg-white/10 border-white/20 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div>
                    <label className="text-white font-medium mb-2 block">Комментарий</label>
                    <Textarea
                      placeholder="Расскажите о ваших требованиях..."
                      value={formData.comment}
                      onChange={(e) => setFormData({ ...formData, comment: e.target.value })}
                      className="bg-white/10 border-white/20 text-white placeholder:text-slate-500 min-h-[100px]"
                    />
                  </div>

                  <Button 
                    type="submit"
                    size="lg"
                    className="w-full bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
                  >
                    <Icon name="Send" size={20} className="mr-2" />
                    Отправить заявку
                  </Button>
                </form>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="py-12 border-t border-white/10">
        <div className="container mx-auto px-4">
          <div className="text-center space-y-4">
            <div className="flex justify-center gap-6">
              <a href="tel:+79001234567" className="text-slate-400 hover:text-white transition-colors flex items-center gap-2">
                <Icon name="Phone" size={20} />
                +7 (900) 123-45-67
              </a>
              <a href="mailto:info@stavlead.ru" className="text-slate-400 hover:text-white transition-colors flex items-center gap-2">
                <Icon name="Mail" size={20} />
                info@stavlead.ru
              </a>
            </div>
            <p className="text-slate-500">
              © 2026 StavLead. Платформа лидов на недвижимость в Ставрополе
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
