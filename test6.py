def multi_split(s, seps):
    parts = []
    curr = ""
    for ch in s:
        if ch in seps:
            # при встрече разделителя — дорисованный токен, если не пустой
            if curr.strip():
                parts.append(curr.strip())
            curr = ""
        else:
            curr += ch
    # плюс последний кусок, если есть
    if curr.strip():
        parts.append(curr.strip())
    return parts



with open("work/test6.bnb","r") as f:
    cod = f.read() 
# cod = cod[0:len(cod)-1]
c = cod.replace("\n", "").replace("\t", "")
firstSplit = multi_split(c, [';', '{'])
print(firstSplit)

spec = ['-', '+', '=', '/', '*', '<', '>', '%', '&', '|', ' ', '(', ')', '#', '$', '!']
vars = []
asm_code = []  # Список для хранения ассемблерных инструкций
asm_data = []  # Список для хранения данных
vars_declared = set()  # Множество для хранения объявленных переменных  

label_counter = 0
if_labels = []  # стек меток конца каждого открытого if

string_counter = 0

string_vars = set()   # здесь будем хранить имена переменных-буферов

# Преобразование списка токенов из инфиксной нотации в обратную польскую
def infix_to_postfix(tokens):
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
    output = []
    stack = []

    i = 0
    while i < len(tokens):
        tok = tokens[i]
        # Объединяем символы для двухсимвольных операторов
        if i + 1 < len(tokens) and tok + tokens[i+1] in precedence:
            tok = tok + tokens[i+1]
            i += 1  # "съели" второй символ
        if tok == '(':
            stack.append(tok)
        elif tok == ')':
            while stack and stack[-1] != '(':
                output.append(stack.pop())
            stack.pop()  # убрать '('
        elif tok in precedence:
            # выталкиваем операторы с >= приоритетом
            while stack and stack[-1] != '(' and precedence[stack[-1]] >= precedence[tok]:
                output.append(stack.pop())
            stack.append(tok)
        else:
            # операнд
            output.append(tok)
        i += 1

    # остаточные операторы
    while stack:
        output.append(stack.pop())

    return output

def extract_if_condition(tokens):
    """
    Из списка токенов, начинающихся с 'if', 
    возвращает подсписок токенов условия.
    Например:
      ['if','a','<','b',':','{', ...] → ['a','<','b']
    """
    assert tokens and tokens[0] == 'if'
    # ищем разделитель ':' или конец списка
    if ':' in tokens:
        idx = tokens.index(':')
        return tokens[1:idx]
    else:
        return tokens[1:]


def rpn_to_masm(tokens):
    """
    Преобразует список токенов в RPN (постфиксная запись) в 
    список строк с MASM-кодом (Irvine32), вычисляющим выражение.
    
    tokens: list[str] — RPN-последовательность, например ['a','b','+','a','+']
    return: list[str] — строки с инструкциями
    """
    asm = []
    for tok in tokens:
        # Если токен — целое число (литерал)
        if tok.lstrip('-').isdigit():
            asm.append(f"    push {tok}")
        # Иначе — предполагаем, что это имя переменной
        elif tok.isidentifier():
            asm.append(f"    push DWORD PTR [{tok}]")
        else:
            # Оператор: достаём два операнда из стека
            asm.append("    pop ebx")
            asm.append("    pop eax")
            if tok == '+':
                asm.append("    add eax, ebx")
                asm.append("    push eax")
            elif tok == '-':
                asm.append("    sub eax, ebx")
                asm.append("    push eax")
            elif tok == '*':
                asm.append("    imul ebx")    # умножение: EAX *= EBX
                asm.append("    push eax")
            elif tok in ('/', '%'):
                asm.append("    cdq")          # расширяем EAX→EDX:EAX
                asm.append("    idiv ebx")     # делим EDX:EAX на EBX
                if tok == '/':
                    asm.append("    push eax")  # деление → в EAX
                else:
                    asm.append("    push edx")  # остаток → в EDX
            else:
                raise ValueError(f"Неизвестный оператор: {tok}")
    return asm

# Пример
# rpn = ['a', 'b', '+', 'a', '+']
# code = rpn_to_masm(rpn)
# print('\n'.join(code))




def ensure_variable(name: str):
    """
    Проверяет, объявлена ли переменная с именем `name`,
    и если нет — добавляет её в vars_declared и в asm_data.
    """
    if name not in vars_declared:
        vars_declared.add(name)
        asm_data.append(f"{name} dd ?")






def new_if_labels():
    """Собираем уникальные метки для одного if…else…EndIf."""
    global label_counter
    L = label_counter
    label_counter += 1
    return f"MakeIf{L}", f"MisIfOrMakeElse{L}", f"MisElse{L}"

def rpn_condition_to_masm(rpn_tokens):
    """
    Превращает RPN-условие вида [..., op] в ASM:
      — арифметика для левого/правого
      — pop ebx / pop eax / cmp / jm Then / jmp Else / Then:
    Возвращает (code_lines, ElseLbl, EndIfLbl).
    """
    # 1) отделяем арифм часть от оператора
    *arith, op = rpn_tokens
    code = rpn_to_masm(arith)

    # 2) выбираем Jcc
    jm_map = {'<':'jl','<=':'jle','>':'jg','>=':'jge','==':'je','!=':'jne'}
    jm = jm_map[op]

    # 3) собираем метки
    then_lbl, else_lbl, endif_lbl = new_if_labels()

    # 4) строим код сравнения + переходы
    code += [
        "    pop ebx",
        "    pop eax",
        "    cmp eax, ebx",
        f"    {jm} {then_lbl}",   # если true → ThenN
        f"    jmp {else_lbl}",     # иначе → ElseN
        f"{then_lbl}:",            # вход в then-блок
    ]
    return code, else_lbl, endif_lbl





def handle_print(secondSplit):
    """
    Обрабатывает команду print:
      - print \"...\";         — выводит строковый литерал (с поддержкой \\n и "")
      - print buf;             — выводит содержимое строкового буфера buf
      - print expr;            — выводит число (результат арифм. выражения)
    """
    rest = secondSplit[1:]
    first = rest[0]

    # 1) Строковой литерал в кавычках
    if first.startswith('"'):
        # собираем весь литерал до закрывающей кавычки
        parts = []
        for tok in rest:
            parts.append(tok)
            if tok.endswith('"'):
                break
        lit = " ".join(parts)
        # удаляем внешние кавычки, обрабатываем ""→" и \"→"
        content = lit[1:-1].replace('""', '"').replace('\\"', '"')

        # разбиваем по "\n" → вставляем 0Dh,0Ah между сегментами
        segs = content.split("\\n")
        data_bytes = []
        for idx, seg in enumerate(segs):
            if seg:
                data_bytes.append(f'"{seg}"')
            if idx < len(segs) - 1:
                data_bytes.append("0Dh,0Ah")
        data_bytes.append("0")  # терминатор

        # создаём метку и объявляем в .data
        lbl = f"str{len(string_vars)}"
        string_vars.add(lbl)  # чтобы счётчик был уникален
        asm_data.append(f"{lbl} BYTE " + ",".join(data_bytes))

        # в .code — выводим через WriteString
        asm_code.append(f"    lea   edx, {lbl}")
        asm_code.append("    call  WriteString")
        return

    # 2) Это одна переменная — возможно, строка-буфер
    if len(rest)==1 and rest[0].rstrip(',') in string_vars:
        var = rest[0].rstrip(',')
        asm_code.append(f"    lea   edx, {var}")
        asm_code.append("    call  WriteString")
        return

    # 3) Всё остальное — арифметическое выражение / число
    rpn = infix_to_postfix(rest)
    seq = rpn_to_masm(rpn)
    asm_code.extend(seq)
    asm_code.append("    pop   eax")
    asm_code.append("    call  WriteInt")


def handle_input(secondSplit):
    rest = secondSplit[1:]
    # всегда «чистим» имя от лишней запятой
    var_token = rest[0].rstrip(',')
    if len(rest) == 1:
        var = var_token
        if var not in vars_declared:
            vars_declared.add(var)
            asm_data.append(f"{var} dd ?")
        asm_code.append("    call ReadInt")
        asm_code.append(f"    mov [{var}], eax")
    else:
        # rest = [ "<buf>,", "64" ] → rstrip и на maxlen тоже можно rstrip(',')
        var = var_token
        maxlen = int(rest[1].rstrip(','))
        if var not in vars_declared:
            vars_declared.add(var)
            asm_data.append(f"{var} BYTE {maxlen} DUP(0)")
            string_vars.add(var)
        asm_code.append(f"    lea   edx, {var}")   # теперь var без запятой
        asm_code.append(f"    mov   ecx, {maxlen}")
        asm_code.append("    call ReadString")




for i in firstSplit:

    secondSplit = i.split(" ")
    print("secondSplit-", secondSplit,"-")

    if secondSplit[0] == "input":
        handle_input(secondSplit)

    elif secondSplit[0] == "print":
        handle_print(secondSplit)

    elif secondSplit[0] == "if":
        cond_tokens = secondSplit[1:secondSplit.index(':')]
        readiSentence = infix_to_postfix(cond_tokens)
        ams_if, else_lbl, endif_lbl = rpn_condition_to_masm(readiSentence)
        asm_code.extend(ams_if)
        if_labels.append(("if", else_lbl, endif_lbl))
        continue

    # —— Обработка else ——
    elif secondSplit[0].startswith("}else"):
        # достаём старый if
        _, old_else, old_end = if_labels.pop()
        # теперь это if-else
        if_labels.append(("if-else", old_else, old_end))
        # генерим переход и метку else
        asm_code.append(f"    jmp {old_end}")
        asm_code.append(f"{old_else}:")
        asm_code.append("    ; — теперь идёт else-блок —")
        continue

    # —— Обработка while (как «зацикленный if») ——
    elif secondSplit[0] == "while":
        cond_tokens = secondSplit[1:secondSplit.index(':')]
        rpn = infix_to_postfix(cond_tokens)
        *arith, op = rpn
        L = label_counter; label_counter += 1
        loop_lbl = f"Loop{L}"
        end_lbl  = f"EndLoop{L}"

        asm_code.append(f"{loop_lbl}:")
        asm_code.extend(rpn_to_masm(arith))
        asm_code += [
            "    pop ebx",
            "    pop eax",
            "    cmp eax, ebx",
            {
                '<':'jge', '<=':'jg',
                '>':'jle', '>=':'jl',
                '==':'jne', '!=':'je'
            }[op] + f" {end_lbl}"
        ]
        if_labels.append(("while", loop_lbl, end_lbl))
        continue

    # —— Закрывающий блок ——
    elif secondSplit[0] == "}":
        if not if_labels:
            continue
        typ, a, b = if_labels.pop()
        if typ == "while":
            asm_code.append(f"    jmp   {a}")
            asm_code.append(f"{b}:")
        elif typ == "if":
            asm_code.append(f"{b}:")
            asm_code.append("    ; — конец блока if без else —")
        else:  # if-else
            asm_code.append(f"{b}:")
            asm_code.append("    ; — конец блока if/else —")
        continue
            
    else:
        if (len(secondSplit) < 3):   # если строка пустая, пропускаем
            continue
        elif (secondSplit[1] == "="):
            readiSentence = infix_to_postfix(secondSplit[2:])
            print("readiSentence ", readiSentence)
            masmCode =rpn_to_masm(readiSentence)
            print("masmCode ", '\n'.join(masmCode))
            asm_code.extend(masmCode)
            # сохраняем результат: pop eax; mov [target], eax
            ensure_variable(secondSplit[0])
            asm_code.append("    pop eax")
            asm_code.append(f"    mov [{secondSplit[0]}], eax")
            asm_code.append("")  # пустая строка для читабельности


















# Запись итогового ассемблерного кода в файл
with open("work/out2.asm","w") as f: # открываем файл для записи
    f.write("""INCLUDE Irvine32.inc

.data\n""") # пишем заголовок и секцию данных
    f.write("\n".join(asm_data))   # пишем объявления переменных
    f.write("""
.code
main PROC\n""") # пишем секцию кода и начало main
    f.write("\n".join(asm_code))   # пишем сгенерированный код
    f.write("""
exit\t 
main ENDP
END main
""") # пишем завершение программы

