# Исправление ActingCardsPage.tsx (Next.js "use client")

Ошибка: `'use client'` должна быть **первой строкой** файла.

## Вариант 1: Применить патч

В папке репо **django-layout-development-main** (тот, что деплоится):

```bash
cd /путь/к/django-layout-development-main
git apply /путь/к/telegram-psychologist-bot/fix-acting-cards-use-client.patch
git add src/pages/ActingCardsPage.tsx
git commit -m "fix: use client at top of ActingCardsPage"
git push
```

## Вариант 2: Вручную

Открой `src/pages/ActingCardsPage.tsx`:

1. В **самую первую строку** файла вставь: `'use client';`
2. Удали строку `'use client';` которая сейчас после импортов (около строки 20).

Должно быть так:

```tsx
'use client';
import { useState, useEffect } from "react";
import { Helmet } from "react-helmet";
// ... остальные импорты ...
```

После этого закоммить, push — и заново деплой.
