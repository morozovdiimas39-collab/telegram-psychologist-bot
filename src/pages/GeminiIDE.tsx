import { useState, useRef, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Textarea } from '@/components/ui/textarea';
import Icon from '@/components/ui/icon';
import { toast } from 'sonner';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export default function GeminiIDE() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Привет! Я Gemini 1.5 Pro - мощный AI ассистент для программирования. Спрашивай что угодно про код!',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    try {
      // Подключение к Gemini API напрямую через браузер
      const API_KEY = 'AIzaSyBheSf96XE7Svv5nDbJvEv-vq2ynS8oIlA';
      const API_URL = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key=${API_KEY}`;

      // Формируем историю для контекста
      const contents = messages
        .filter(m => m.role !== 'assistant' || messages.indexOf(m) < messages.length)
        .map(m => ({
          role: m.role === 'assistant' ? 'model' : 'user',
          parts: [{ text: m.content }]
        }));

      contents.push({
        role: 'user',
        parts: [{ text: input }]
      });

      const response = await fetch(API_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          contents,
          generationConfig: {
            temperature: 0.7,
            topK: 40,
            topP: 0.95,
            maxOutputTokens: 8192,
          }
        })
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error?.message || 'Ошибка API');
      }

      const data = await response.json();
      const aiResponse = data.candidates[0].content.parts[0].text;

      const assistantMessage: Message = {
        role: 'assistant',
        content: aiResponse,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error: any) {
      toast.error(`Ошибка: ${error.message}`);
      console.error('Gemini API Error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const clearChat = () => {
    setMessages([{
      role: 'assistant',
      content: 'Чат очищен! Чем могу помочь?',
      timestamp: new Date()
    }]);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-purple-950 to-slate-950 p-4">
      <div className="container mx-auto max-w-5xl py-8">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
              <span className="text-5xl">🤖</span>
              Gemini IDE
            </h1>
            <p className="text-slate-400">
              Бесплатная платформа разработки на базе Gemini 2.0 Flash Experimental
            </p>
          </div>
          <Button 
            variant="outline" 
            onClick={clearChat}
            className="border-white/20 text-white hover:bg-white/10"
          >
            <Icon name="Trash2" size={18} className="mr-2" />
            Очистить
          </Button>
        </div>

        {/* Chat Area */}
        <Card className="bg-white/5 backdrop-blur border-white/10 mb-4">
          <CardContent className="p-6">
            <div className="h-[60vh] overflow-y-auto space-y-4 mb-4">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'assistant' && (
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                      <span className="text-xl">🤖</span>
                    </div>
                  )}
                  <div
                    className={`max-w-[75%] rounded-2xl p-4 ${
                      msg.role === 'user'
                        ? 'bg-gradient-to-br from-blue-600 to-purple-600 text-white'
                        : 'bg-white/10 text-white border border-white/20'
                    }`}
                  >
                    <div className="prose prose-invert max-w-none">
                      <p className="whitespace-pre-wrap">{msg.content}</p>
                    </div>
                    <div className="text-xs opacity-60 mt-2">
                      {msg.timestamp.toLocaleTimeString('ru-RU', {
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </div>
                  </div>
                  {msg.role === 'user' && (
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-teal-500 flex items-center justify-center flex-shrink-0">
                      <Icon name="User" size={20} className="text-white" />
                    </div>
                  )}
                </div>
              ))}
              {isLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center">
                    <span className="text-xl">🤖</span>
                  </div>
                  <div className="bg-white/10 border border-white/20 rounded-2xl p-4">
                    <div className="flex gap-2">
                      <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                      <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                      <div className="w-2 h-2 bg-white rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="flex gap-3">
              <Textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Напиши свой вопрос... (Enter для отправки, Shift+Enter для новой строки)"
                className="bg-white/10 border-white/20 text-white placeholder:text-slate-500 resize-none"
                rows={3}
                disabled={isLoading}
              />
              <Button
                onClick={sendMessage}
                disabled={!input.trim() || isLoading}
                className="bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 h-auto px-6"
              >
                <Icon name="Send" size={20} />
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Info Cards */}
        <div className="grid md:grid-cols-3 gap-4">
          <Card className="bg-white/5 backdrop-blur border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 mb-2">
                <Icon name="Zap" size={24} className="text-yellow-400" />
                <h3 className="text-white font-bold">Бесплатно</h3>
              </div>
              <p className="text-sm text-slate-400">
                Никаких ограничений и платных подписок
              </p>
            </CardContent>
          </Card>

          <Card className="bg-white/5 backdrop-blur border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 mb-2">
                <Icon name="Code2" size={24} className="text-blue-400" />
                <h3 className="text-white font-bold">Для разработки</h3>
              </div>
              <p className="text-sm text-slate-400">
                Генерация кода, отладка, оптимизация
              </p>
            </CardContent>
          </Card>

          <Card className="bg-white/5 backdrop-blur border-white/10">
            <CardContent className="p-4">
              <div className="flex items-center gap-3 mb-2">
                <Icon name="Sparkles" size={24} className="text-purple-400" />
                <h3 className="text-white font-bold">Мощный AI</h3>
              </div>
              <p className="text-sm text-slate-400">
                Gemini 2.0 Flash Experimental
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Warning */}
        <div className="mt-6 p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-lg">
          <div className="flex items-start gap-3">
            <Icon name="AlertTriangle" size={20} className="text-yellow-400 mt-0.5" />
            <div className="text-sm text-yellow-200">
              <strong>Важно:</strong> API ключ встроен в код для демонстрации. 
              В продакшене используйте переменные окружения и backend для безопасности.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}