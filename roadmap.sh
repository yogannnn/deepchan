#!/data/data/com.termux/files/usr/bin/bash
# roadmap.sh - управление статусами пунктов в ROADMAP.md
# Использование:
#   ./roadmap.sh list            - показать все пункты (сгруппированы)
#   ./roadmap.sh list <номер>    - показать конкретный пункт с контекстом
#   ./roadmap.sh check <номер>   - отметить пункт как выполненный [x]
#   ./roadmap.sh uncheck <номер> - снять отметку [ ]

ROADMAP_FILE="ROADMAP.md"

if [ ! -f "$ROADMAP_FILE" ]; then
    echo "❌ Файл $ROADMAP_FILE не найден."
    exit 1
fi

show_usage() {
    echo "Использование: $0 <команда> [аргумент]"
    echo "Команды:"
    echo "  list               - показать все пункты (сгруппированы)"
    echo "  list <номер>       - показать пункт с контекстом"
    echo "  check <номер>      - отметить пункт как выполненный [x]"
    echo "  uncheck <номер>    - снять отметку [ ]"
    echo "  help               - показать эту справку"
    exit 0
}

if [ $# -eq 0 ]; then
    show_usage
fi

ACTION="$1"

case "$ACTION" in
    list)
        if [ $# -eq 1 ]; then
            # Вывести все пункты с подсветкой категорий
            echo "📋 Все пункты дорожной карты:"
            grep -n "^- \[[ x]\]" "$ROADMAP_FILE" | while IFS= read -r line; do
                num=$(echo "$line" | cut -d: -f1)
                text=$(echo "$line" | cut -d: -f2-)
                # Определяем категорию по предыдущим строкам (простой способ: запоминаем последний заголовок ##)
                # Для красоты просто выводим с номером строки
                echo "$text"
            done
        else
            ITEM="$2"
            # Найти пункт и показать с контекстом (5 строк до и 2 после)
            LINE_NUM=$(grep -n "^- \[[ x]\] $ITEM\. " "$ROADMAP_FILE" | cut -d: -f1 | head -1)
            if [ -z "$LINE_NUM" ]; then
                echo "❌ Пункт $ITEM не найден."
                exit 1
            fi
            echo "📌 Пункт $ITEM:"
            # Показываем контекст
            START=$((LINE_NUM > 5 ? LINE_NUM - 5 : 1))
            END=$((LINE_NUM + 2))
            sed -n "${START},${END}p" "$ROADMAP_FILE"
        fi
        ;;
    check)
        if [ $# -ne 2 ]; then
            echo "❌ Укажите номер пункта."
            exit 1
        fi
        ITEM="$2"
        # Заменяем "- [ ] N." на "- [x] N."
        sed -i "s/^- \[ \] $ITEM\. /- [x] $ITEM. /" "$ROADMAP_FILE"
        echo "✅ Пункт $ITEM отмечен как выполненный."
        ;;
    uncheck)
        if [ $# -ne 2 ]; then
            echo "❌ Укажите номер пункта."
            exit 1
        fi
        ITEM="$2"
        # Заменяем "- [x] N." на "- [ ] N."
        sed -i "s/^- \[x\] $ITEM\. /- [ ] $ITEM. /" "$ROADMAP_FILE"
        echo "🔄 Пункт $ITEM снят с выполнения."
        ;;
    help)
        show_usage
        ;;
    *)
        echo "❌ Неизвестная команда: $ACTION"
        show_usage
        ;;
esac
