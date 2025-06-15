def multi_split(s, seps):  # разбивает строку s по списку разделителей seps
    parts = []  # список для хранения частей
    curr = ""  # текущий токен
    for ch in s:  # перебираем каждый символ в s
        if ch in seps:  # если символ — один из разделителей
            # при встрече разделителя — дорисованный токен, если не пустой
            if curr.strip():  # если текущий токен после .strip() не пуст
                parts.append(curr.strip())  # добавляем токен в parts
            curr = ""  # сбрасываем токен
        else:
            curr += ch  # иначе накапливаем символ в curr
    # плюс последний кусок, если есть
    if curr.strip():  # если после цикла в curr что-то осталось
        parts.append(curr.strip())  # добавляем последний токен
    return parts  # возвращаем список частей



with open("work/test7.bnb","r") as f:  # открываем исходный файл
    cod = f.read()  # читаем весь текст в cod
# cod = cod[0:len(cod)-1]
c = cod.replace("\n", "").replace("\t", "")  # удаляем переводы строк и табы
firstSplit = multi_split(c, [';', '{'])  # разбиваем на команды по ‘;’ и ‘{’
print(firstSplit)  # выводим список команд

spec = ['-', '+', '=', '/', '*', '<', '>', '%', '&', '|', ' ', '(', ')', '#', '$', '!']  # все операторы и спецсимволы
vars = []  # (пока не используется) список переменных
asm_code = []  # список ассемблерных инструкций для секции .code
asm_data = []  # список объявлений для секции .data
vars_declared = set()  # множество объявленных переменных  

label_counter = 0  # счётчик для генерации уникальных меток
if_labels = []  # стек меток для if/else/while блоков

string_counter = 0  # (не используется) счётчик строковых литералов

string_vars = set()   # множество имён строковых буферов

# Преобразование списка токенов из инфиксной нотации в обратную польскую
def infix_to_postfix(tokens):  # переводит инфиксную запись в RPN
    """
    Преобразует список токенов в инфиксной нотации в RPN, 
    поддерживает арифметику и сравнения.
    """
    # Приоритет операторов: сравнения ниже чем арифметика
    precedence = {
        '||': 1, '&&': 2,
        '==': 3, '!=': 3, '<': 3, '>': 3, '<=': 3, '>=': 3,
        '+': 4, '-': 4,
        '*': 5, '/': 5, '%': 5,
    }
    output = []  # выходная очередь для RPN
    stack = []  # стек операторов

    i = 0  # индекс текущего токена
    while i < len(tokens):  # пока не дошли до конца списка
        tok = tokens[i]  # текущий токен
        # Объединяем символы для двухсимвольных операторов
        if i + 1 < len(tokens) and tok + tokens[i+1] in precedence:  # если следующий символ формирует оператор
            tok = tok + tokens[i+1]  # сливаем с ним
            i += 1  # пропускаем второй символ
        if tok == '(':  # если открывающая скобка
            stack.append(tok)  # кладём в стек
        elif tok == ')':  # если закрывающая скобка
            while stack and stack[-1] != '(':  # до первой открывающей
                output.append(stack.pop())  # выталкиваем операторы
            stack.pop()  # убираем '('
        elif tok in precedence:  # если оператор
            # выталкиваем операторы с >= приоритетом
            while stack and stack[-1] != '(' and precedence[stack[-1]] >= precedence[tok]:
                output.append(stack.pop())  # перемещаем из стека в output
            stack.append(tok)  # затем кладём текущий оператор
        else:
            # операнд
            output.append(tok)  # сразу в output
        i += 1  # следующий токен

    # остаточные операторы
    while stack:  # пока стек не пуст
        output.append(stack.pop())  # выталкиваем всё в output

    return output  # возвращаем RPN токены

def extract_if_condition(tokens):  # извлекает условие из токенов if
    """
    Из списка токенов, начинающихся с 'if', 
    возвращает подсписок токенов условия.
    Например:
      ['if','a','<','b',':','{', ...] → ['a','<','b']
    """
    assert tokens and tokens[0] == 'if'  # убеждаемся, что это if
    # ищем разделитель ':' или конец списка
    if ':' in tokens:  # если есть ':'
        idx = tokens.index(':')  # находим его индекс
        return tokens[1:idx]  # возвращаем всё между if и :
    else:
        return tokens[1:]  # иначе возвращаем всё после if


def rpn_to_masm(tokens):  # переводит RPN токены в MASM инструкции
    """
    Преобразует список токенов в RPN (постфиксная запись) в 
    список строк с MASM-кодом (Irvine32), вычисляющим выражение.
    
    tokens: list[str] — RPN-последовательность, например ['a','b','+','a','+']
    return: list[str] — строки с инструкциями
    """
    asm = []  # накопитель инструкций
    for tok in tokens:  # для каждого токена
        # Если токен — целое число (литерал)
        if tok.lstrip('-').isdigit():  
            asm.append(f"    push {tok}")  # push литерала
        # Иначе — предполагаем, что это имя переменной
        elif tok.isidentifier():
            asm.append(f"    push DWORD PTR [{tok}]")  # push значения переменной
        else:
            # Оператор: достаём два операнда из стека
            asm.append("    pop ebx")  # pop второй операнд
            asm.append("    pop eax")  # pop первый операнд
            if tok == '+':  
                asm.append("    add eax, ebx")  # складываем
                asm.append("    push eax")  # push результата
            elif tok == '-':  
                asm.append("    sub eax, ebx")  # вычитаем
                asm.append("    push eax")  # push результата
            elif tok == '*':  
                asm.append("    imul ebx")    # умножаем
                asm.append("    push eax")  # push результата
            elif tok in ('/', '%'):  
                asm.append("    cdq")          # расширяем EAX→EDX:EAX
                asm.append("    idiv ebx")     # делим на EBX
                if tok == '/':  
                    asm.append("    push eax")  # push результата деления
                else:
                    asm.append("    push edx")  # push остатка деления
            else:
                raise ValueError(f"Неизвестный оператор: {tok}")  # неизвестный оператор
    return asm  # возвращаем список инструкций

# Пример
# rpn = ['a', 'b', '+', 'a', '+']
# code = rpn_to_masm(rpn)
# print('\n'.join(code))




def ensure_variable(name: str):  # объявляет переменную в .data, если ещё не объявлена
    """
    Проверяет, объявлена ли переменная с именем `name`,
    и если нет — добавляет её в vars_declared и в asm_data.
    """
    if name not in vars_declared:  # если новой нет в множестве
        vars_declared.add(name)  # регистрируем её
        asm_data.append(f"{name} dd ?")  # добавляем объявление

def new_if_labels():  # генерирует уникальные метки для блока if…else
    """Собираем уникальные метки для одного if…else…EndIf."""
    global label_counter  # используем внешний счётчик
    L = label_counter  # текущий номер
    label_counter += 1  # увеличиваем счётчик
    return f"MakeIf{L}", f"MisIfOrMakeElse{L}", f"MisElse{L}"  # возвращаем три метки

def rpn_condition_to_masm(rpn_tokens):  # создаёт ASM для RPN-условия
    """
    Превращает RPN-условие вида [..., op] в ASM:
      — арифметика для левого/правого
      — pop ebx / pop eax / cmp / jm Then / jmp Else / Then:
    Возвращает (code_lines, ElseLbl, EndIfLbl).
    """
    # 1) отделяем арифм часть от оператора
    *arith, op = rpn_tokens  # последний токен — оператор
    code = rpn_to_masm(arith)  # код арифметики

    # 2) выбираем Jcc
    jm_map = {'<':'jl','<=':'jle','>':'jg','>=':'jge','==':'je','!=':'jne'}  # карта переходов
    jm = jm_map[op]  # нужный переход

    # 3) собираем метки
    then_lbl, else_lbl, endif_lbl = new_if_labels()  # получаем метки

    # 4) строим код сравнения + переходы
    code += [
        "    pop ebx",  # pop второго операнда
        "    pop eax",  # pop первого операнда
        "    cmp eax, ebx",  # сравнение
        f"    {jm} {then_lbl}",   # если true → then_lbl
        f"    jmp {else_lbl}",     # иначе → else_lbl
        f"{then_lbl}:",            # метка then
    ]
    return code, else_lbl, endif_lbl  # возвращаем код и метки





def handle_print(secondSplit):  # обрабатывает команду print
    """
    Обрабатывает команду print:
      - print \"...\";         — выводит строковый литерал (с поддержкой \\n и "")
      - print buf;             — выводит содержимое строкового буфера buf
      - print expr;            — выводит число (результат арифм. выражения)
    """
    rest = secondSplit[1:]  # аргументы после 'print'
    first = rest[0]  # первый аргумент

    # 1) Строковой литерал в кавычках
    if first.startswith('"'):  # если начинается с кавычки
        # собираем весь литерал до закрывающей кавычки
        parts = []  # буфер токенов литерала
        for tok in rest:  # пока не встретится конец литерала
            parts.append(tok)  # добавляем токен
            if tok.endswith('"'):  # конец литерала
                break  # выходим из цикла
        lit = " ".join(parts)  # склеиваем токены
        # удаляем внешние кавычки, обрабатываем ""→" и \"→"
        content = lit[1:-1].replace('""', '"').replace('\\"', '"')  # чистим экранирование

        # разбиваем по "\n" → вставляем 0Dh,0Ah между сегментами
        segs = content.split("\\n")  # список сегментов по \n
        data_bytes = []  # байты для .data
        for idx, seg in enumerate(segs):  # для каждого сегмента
            if seg:  # если сегмент не пустой
                data_bytes.append(f'"{seg}"')  # добавляем сегмент
            if idx < len(segs) - 1:  # если не последний сегмент
                data_bytes.append("0Dh,0Ah")  # добавляем CR+LF
        data_bytes.append("0")  # терминатор строки

        # создаём метку и объявляем в .data
        lbl = f"str{len(string_vars)}"  # уникальная метка
        string_vars.add(lbl)  # сохраняем имя метки
        asm_data.append(f"{lbl} BYTE " + ",".join(data_bytes))  # объявление в .data

        # в .code — выводим через WriteString
        asm_code.append(f"    lea   edx, {lbl}")  # загружаем адрес метки
        asm_code.append("    call  WriteString")  # вызываем WriteString
        return  # выходим из функции

    # 2) Это одна переменная — возможно, строка-буфер
    if len(rest)==1 and rest[0].rstrip(',') in string_vars:  # если имя буфера
        var = rest[0].rstrip(',')  # очищаем от запятой
        asm_code.append(f"    lea   edx, {var}")  # загружаем адрес буфера
        asm_code.append("    call  WriteString")  # выводим буфер
        return  # выходим из функции

    # 3) Всё остальное — арифметическое выражение / число
    rpn = infix_to_postfix(rest)  # переводим в RPN
    seq = rpn_to_masm(rpn)  # генерируем ASM из RPN
    asm_code.extend(seq)  # добавляем инструкции
    asm_code.append("    pop   eax")  # pop результата в eax
    asm_code.append("    call  WriteInt")  # выводим целое


def handle_input(secondSplit):  # обрабатывает команду input
    rest = secondSplit[1:]  # аргументы после 'input'
    # всегда «чистим» имя от лишней запятой
    var_token = rest[0].rstrip(',')  # имя переменной или буфера
    if len(rest) == 1:  # если передан только буфер без длины
        var = var_token  # имя переменной
        if var not in vars_declared:  # если переменная не объявлена
            vars_declared.add(var)  # регистрируем её
            asm_data.append(f"{var} dd ?")  # объявляем в .data как dd
        asm_code.append("    call ReadInt")  # вызов ReadInt
        asm_code.append(f"    mov [{var}], eax")  # сохраняем результат
    else:
        # rest = [ "<buf>,", "64" ] → rstrip и на maxlen тоже можно rstrip(',')
        var = var_token  # имя буфера
        maxlen = int(rest[1].rstrip(','))  # максимальная длина буфера
        if var not in vars_declared:  # если буфер не объявлен
            vars_declared.add(var)  # регистрируем буфер
            asm_data.append(f"{var} BYTE {maxlen} DUP(0)")  # объявляем массив байт
            string_vars.add(var)  # сохраняем имя буфера
        asm_code.append(f"    lea   edx, {var}")   # загружаем адрес буфера
        asm_code.append(f"    mov   ecx, {maxlen}")  # загружаем длину буфера
        asm_code.append("    call ReadString")  # вызов ReadString



for i in firstSplit:  # проходим по списку команд

    secondSplit = i.split(" ")  # разбиваем команду на токены
    
    print("secondSplit-", secondSplit,"-")  # отладочный вывод токенов

    if secondSplit[0] == "input":  # если команда input
        print(secondSplit[0])  # отладка: выявление команды
        handle_input(secondSplit)  # вызываем обработчик

    elif secondSplit[0] == "print":  # если команда print
        print(secondSplit[0])  # отладка: выявление команды
        handle_print(secondSplit)  # вызываем обработчик

    elif secondSplit[0] == "if":  # если команда if
        print(secondSplit[0])  # отладка: выявление команды
        cond_tokens = secondSplit[1:secondSplit.index(':')]  # токены условия
        readiSentence = infix_to_postfix(cond_tokens)  # RPN условие
        ams_if, else_lbl, endif_lbl = rpn_condition_to_masm(readiSentence)  # ASM для условия
        asm_code.extend(ams_if)  # добавляем ASM
        if_labels.append(("if", else_lbl, endif_lbl))  # сохраняем метки
        continue  # переходим к следующей команде

    # —— Обработка else ——
    elif secondSplit[0].startswith("}else"):  # если else
        print(secondSplit[0])  # отладка: выявление else
        # достаём старый if
        _, old_else, old_end = if_labels.pop()  # получаем старые метки
        # теперь это if-else
        if_labels.append(("if-else", old_else, old_end))  # сохраняем новые метки
        # генерим переход и метку else
        asm_code.append(f"    jmp {old_end}")  # переход к концу if
        asm_code.append(f"{old_else}:")  # метка начала else
        asm_code.append("    ; — теперь идёт else-блок —")  # комментарий блока
        continue  # далее

    # —— Обработка while (как «зацикленный if») ——
    elif secondSplit[0] == "while":  # если while
        print(secondSplit[0])  # отладка: выявление while
        cond_tokens = secondSplit[1:secondSplit.index(':')]  # токены условия
        rpn = infix_to_postfix(cond_tokens)  # RPN условие
        *arith, op = rpn  # арифм. часть и оператор
        L = label_counter; label_counter += 1  # генерируем новую метку
        loop_lbl = f"Loop{L}"  # метка начала цикла
        end_lbl  = f"EndLoop{L}"  # метка конца цикла

        asm_code.append(f"{loop_lbl}:")  # вставляем метку начала
        asm_code.extend(rpn_to_masm(arith))  # код для проверяемого выражения
        asm_code += [
            "    pop ebx",  # pop второго операнда
            "    pop eax",  # pop первого операнда
            "    cmp eax, ebx",  # сравнение
            {
                '<':'jge', '<=':'jg',  # карты переходов
                '>':'jle', '>=':'jl',
                '==':'jne', '!=':'je'
            }[op] + f" {end_lbl}"  # условный переход
        ]
        if_labels.append(("while", loop_lbl, end_lbl))  # сохраняем метки
        continue  # дальше

    # —— Закрывающий блок ——
    elif secondSplit[0] == "}":  # если закрытие блока
        print(secondSplit[0])  # отладка: закрылся блок
        if not if_labels:  # если стек пуст
            continue  # ничего не делаем
        typ, a, b = if_labels.pop()  # извлекаем метки
        if typ == "while":  # если это цикл
            asm_code.append(f"    jmp   {a}")  # переход к началу
            asm_code.append(f"{b}:")  # метка конца цикла
        elif typ == "if":  # если одинарный if
            asm_code.append(f"{a}:")  # метка конца if
            asm_code.append("    ; — конец блока if без else —")  # комментарий
        else:  # if-else
            asm_code.append(f"{b}:")  # метка конца else
            asm_code.append("    ; — конец блока if/else —")  # комментарий
        continue  # дальше
            
    else:
        if (len(secondSplit) < 3):   # если строка пустая или слишком короткая
            continue  # пропускаем
        elif (secondSplit[1] == "="):  # если присваивание
            print(secondSplit[0])  # отладка: имя переменной
            readiSentence = infix_to_postfix(secondSplit[2:])  # RPN правой части
            print("readiSentence ", readiSentence)  # вывод RPN
            masmCode =rpn_to_masm(readiSentence)  # ASM из RPN
            print("masmCode ", '\n'.join(masmCode))  # отладка ASM
            asm_code.extend(masmCode)  # добавляем ASM инструкции
            # сохраняем результат: pop eax; mov [target], eax
            ensure_variable(secondSplit[0])  # объявляем переменную, если надо
            asm_code.append("    pop eax")  # pop результата
            asm_code.append(f"    mov [{secondSplit[0]}], eax")  # mov обратно в память
            asm_code.append("")  # пустая строка для читабельности


















# Запись итогового ассемблерного кода в файл
with open("work/out7.asm","w") as f:  # открываем файл вывода
    f.write("""INCLUDE Irvine32.inc

.data\n""")  # пишем заголовок и секцию данных
    f.write("\n".join(asm_data))   # записываем объявления переменных
    f.write("""
.code
main PROC\n""")  # пишем начало секции .code и main
    f.write("\n".join(asm_code))   # записываем все инструкции
    f.write("""
exit\t 
main ENDP
END main
""")  # пишем завершение программы
