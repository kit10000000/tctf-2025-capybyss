# Capybyss TCTF 2025

## Описание задачи

![alt text](<Screenshot 2025-04-20 181200.png>)

## Входные данные:

1. Файл censored_checker_5436028.elf
2. Видео с созданием файла 

## Команды из видео (аналогичные):

```
┌──(user㉿kali)-[]
└─$ ls -alt
total 16
drwxr-xr-x 2 root root 4096 Apr 20 18:03 .
drwxr-xr-x 5 root root 4096 Apr 20 18:03 ..
-rwxr-xr-x 1 user  user    39 Apr 20 18:00 flag.c
-rwxr-xr-x 1 user  user   372 Apr 20 17:59 checker.c

┌──(user㉿kali)-[]
└─$ cat checker.c                                               
#include <stdio.h>
#include <string.h>

int main(int argc, char ** argv)
{
    char correct_flag[]=
#include "flag.c"
    ;
    if (argc != 2) {
        printf("usage");
        return 1;
    }
    if ((strcmp(argv[1], correct_flag)) == 0) {
        printf("correct!");
        return 0;
    } else{
        printf("not correct!");
        return 1;
    }
    return 0;
}
                            
┌──(user㉿kali)-[]
└─$ sudo gcc -o checker checker.c
                                                       
┌──(user㉿kali)-[]
└─$ ls -alt
total 32
-rwxr-xr-x 1 root root 16008 Apr 20 18:05 checker
drwxr-xr-x 2 root root  4096 Apr 20 18:05 .
drwxr-xr-x 5 root root  4096 Apr 20 18:03 ..
-rwxr-xr-x 1 user  user     39 Apr 20 18:00 flag.c
-rwxr-xr-x 1 user  user    372 Apr 20 17:59 checker.c
                                   
┌──(user㉿kali)-[]
└─$ file checker                   
checker: ELF 64-bit LSB pie executable, x86-64, version 1 (SYSV), dynamically linked, interpreter /lib64/ld-linux-x86-64.so.2, BuildID[sha1]=f181c1b15354aadc2bb47c97b161d987adec9cf4, for GNU/Linux 3.2.0, not stripped
                             
┌──(user㉿kali)-[]
└─$ sudo echo -n "????????" | sudo dd of=censored_checker bs=1 seek=$((0x1176)) conv=notrunc
8+0 records in
8+0 records out
8 bytes copied, 0.00151843 s, 5.3 kB/s
                                    
┌──(user㉿kali)-[]
└─$ ls -alt
total 48
-rwxr-xr-x 1 root root 16008 Apr 20 18:14 censored_checker
drwxr-xr-x 2 root root  4096 Apr 20 18:12 .
-rwxr-xr-x 1 root root 16008 Apr 20 18:10 checker
-rwxr-xr-x 1 user  user     41 Apr 20 18:10 flag.c
drwxr-xr-x 5 root root  4096 Apr 20 18:03 ..
-rwxr-xr-x 1 user  user    372 Apr 20 17:59 checker.c
                                  
┌──(user㉿kali)-[]
└─$ md5sum censored_checker 
e47f086768ad795e3b5c19024dd93856  censored_checker
                              
┌──(user㉿kali)-[]
└─$ sudo mv censored_checker censored_checker_e47f08.elf

```


## Объяснение решения

В ELF-файле присутствует секция .note.gnu.build-id, содержащая build-id, вычисленный линковщиком ld. GNU build-id — это криптографический хэш (SHA-1), который линковщик вычисляет после линковки, на основе содержимого ELF-файла (определённого набора заголовков и секций).

```
$ file censored_checker_5436028.elf
ELF 64-bit LSB pie executable, x86-64, dynamically linked,
BuildID[sha1]=eeb1c4e54c7adc376da8365448d43331de23fb18
```

Затёртые байты находятся в секции .text, которая влияет на значение build-id. Поскольку байты были затёрты уже после компиляции и линковки, build-id в ELF соответствует версии файла с исходными (не затёртыми) байтами.

Для решения задачи необходимо воспроизвести алгоритм вычисления build-id, а затем подобрать такие значения затёртых байт, при которых результат SHA-1 совпадёт с известным build-id.

Для этого будет реализован скрипт, который воспроизводит логику генерации build-id линковщиком ld. После этого алгоритм используется для перебора возможных значений затёртых байт.

Для ускорения перебора используется инкрементальное хэширование: пересчитывается только та часть SHA-1, которая зависит от подставляемых байт, тогда как неизменная часть вычисляется один раз.

Примерная логика работы скрипта:
1. Вычисляется и сохраняется поток байт, передаваемых в SHA-1 до затёртого диапазона (префикс);
2. Сохраняется поток байт, передаваемых в SHA-1 после затёртого диапазона (суффикс);
3. Перебираются все комбинации длиной 8 байт из алфавита 0123456789abcdef (так как флаг имеет hex-формат);
    3.1. Для каждой комбинации вычисляется SHA1(префикс + candidate +  суффикс)и результат сравнивается с известным значением build-id;
4.При совпадении искомые байты флага считаются восстановленными.


## Некоторые этапы решения (некоторые названия программ могут не совпадать, тк для решения использовался ARM)

### Скачивание и сборка исходников ld

1. Определение версии ld 
```
┌──(user㉿kali)-[~]
└─$ which x86_64-linux-gnu-gcc
/usr/bin/x86_64-linux-gnu-gcc

┌──(user㉿kali)-[~]
└─$ x86_64-linux-gnu-gcc -print-prog-name=ld
/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/bin/ld

┌──(user㉿kali)-[~]
└─$ x86_64-linux-gnu-gcc -Wl,--version
collect2 version 15.2.0
/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/bin/ld -plugin /usr/libexec/gcc-cross/x86_64-linux-gnu/15/liblto_plugin.so -plugin-opt=/usr/libexec/gcc-cross/x86_64-linux-gnu/15/lto-wrapper -plugin-opt=-fresolution=/tmp/ccDzwYwr.res -plugin-opt=-pass-through=-lgcc -plugin-opt=-pass-through=-lgcc_s -plugin-opt=-pass-through=-lc -plugin-opt=-pass-through=-lgcc -plugin-opt=-pass-through=-lgcc_s --sysroot=/ --build-id --eh-frame-hdr -m elf_x86_64 --hash-style=gnu --as-needed -dynamic-linker /lib64/ld-linux-x86-64.so.2 -pie /usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/Scrt1.o /usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crti.o /usr/lib/gcc-cross/x86_64-linux-gnu/15/crtbeginS.o -L/usr/lib/gcc-cross/x86_64-linux-gnu/15 -L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib -L/lib/x86_64-linux-gnu -L/lib/../lib -L/usr/lib/x86_64-linux-gnu -L/usr/lib/../lib -L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib -L/lib -L/usr/lib --version -lgcc --push-state --as-needed -lgcc_s --pop-state -lc -lgcc --push-state --as-needed -lgcc_s --pop-state /usr/lib/gcc-cross/x86_64-linux-gnu/15/crtendS.o /usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crtn.o
GNU ld (GNU Binutils for Debian) 2.45.50.20251209
Copyright (C) 2025 Free Software Foundation, Inc.
This program is free software; you may redistribute it under the terms of
the GNU General Public License version 3 or (at your option) a later version.
This program has absolutely no warranty.
```
2. Скачивание исходников (предварительно добавить репозиторий deb-src в /etc/apt/sources.list)

```
┌──(user㉿kali)-[~]
└─$ apt-get source binutils=2.45.50.20251209-1
```
```
cd binutils-2.45.50.20251209
mkdir build-gdb
cd build-gdb

../configure --disable-werror \
  --build=aarch64-unknown-linux-gnu \
  --host=aarch64-unknown-linux-gnu \
  --target=x86_64-linux-gnu \
  CFLAGS="-O0 -g"

make -j$(nproc) all-ld

## должно быть no stripped для дебага ("with debug_info, not stripped")
file build-gdb/ld/ld-new 
```

## Создаем свой checker для отладки, чтобы мы знали все байты файла
1. В checker.c сохраняем код из скрипта выше;
2. В flag.c свой флаг в формате tctf{md5hash};
3. Запускаем gcc с strace, чтобы получить все опции для запуска ld:
```
strace -f -s 12000 -o trace.txt x86_64-linux-gnu-gcc -o checker_checked_debug_learn checker.c
```
команда ld из strace:

```
59646 execve("/usr/libexec/gcc-cross/x86_64-linux-gnu/15/collect2", ["/usr/libexec/gcc-cross/x86_64-linux-gnu/15/collect2", "-plugin", "/usr/libexec/gcc-cross/x86_64-linux-gnu/15/liblto_plugin.so", "-plugin-opt=/usr/libexec/gcc-cross/x86_64-linux-gnu/15/lto-wrapper", "-plugin-opt=-fresolution=/tmp/ccKerzZh.res", "-plugin-opt=-pass-through=-lgcc", "-plugin-opt=-pass-through=-lgcc_s", "-plugin-opt=-pass-through=-lc", "-plugin-opt=-pass-through=-lgcc", "-plugin-opt=-pass-through=-lgcc_s", "--sysroot=/", "--build-id", "--eh-frame-hdr", "-m", "elf_x86_64", "--hash-style=gnu", "--as-needed", "-dynamic-linker", "/lib64/ld-linux-x86-64.so.2", "-pie", "-o", "checker_checked_debug_learn", "/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/Scrt1.o", "/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crti.o", "/usr/lib/gcc-cross/x86_64-linux-gnu/15/crtbeginS.o", "-L/usr/lib/gcc-cross/x86_64-linux-gnu/15", "-L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib", "-L/lib/x86_64-linux-gnu", "-L/lib/../lib", "-L/usr/lib/x86_64-linux-gnu", "-L/usr/lib/../lib", "-L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib", "-L/lib", "-L/usr/lib", "[МЕНЯЕМ НА ПУТЬ ДО ОБЪЕКТНОГО ФАЙЛА]", "-lgcc", "--push-state", "--as-needed", "-lgcc_s", "--pop-state", "-lc", "-lgcc", "--push-state", "--as-needed", "-lgcc_s", "--pop-state", "/usr/lib/gcc-cross/x86_64-linux-gnu/15/crtendS.o", "/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crtn.o"]...)
```
4. Теперь запускаем gcc и создаем только объектный файл:
```
x86_64-linux-gnu-gcc -c checker.c -o checker_debug.o -mtune=generic -march=x86-64 -fPIE
```
5. Далее запускаем наш скомпилировнный ld на нашем .o файле

```
┌──(user㉿kali)-[~/Desktop/flag_checker/binutils-2.45.50.20251209/build-gdb/ld]
└─$ ./ld-new -plugin /usr/libexec/gcc-cross/x86_64-linux-gnu/15/liblto_plugin.so \
-plugin-opt=/usr/libexec/gcc-cross/x86_64-linux-gnu/15/lto-wrapper \
-plugin-opt=-fresolution=/tmp/ccKerzZh.res \
-plugin-opt=-pass-through=-lgcc \
-plugin-opt=-pass-through=-lgcc_s \
-plugin-opt=-pass-through=-lc \
-plugin-opt=-pass-through=-lgcc \
-plugin-opt=-pass-through=-lgcc_s \
--sysroot=/ \
--build-id \
--eh-frame-hdr \
-m  elf_x86_64 \
--hash-style=gnu \
--as-needed \
--dynamic-linker /lib64/ld-linux-x86-64.so.2 \
-pie \
-o checker_checked_debug_learn \
/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/Scrt1.o \
/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crti.o \
/usr/lib/gcc-cross/x86_64-linux-gnu/15/crtbeginS.o \
-L/usr/lib/gcc-cross/x86_64-linux-gnu/15 \
-L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib \
-L/lib/x86_64-linux-gnu \
-L/lib/../lib \
-L/usr/lib/x86_64-linux-gnu \
-L/usr/lib/../lib \
-L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib \
-L/lib \
-L/usr/lib \
/home/user/Desktop/flag_checker/checker_debug.o \
-lgcc \
--push-state --as-needed -lgcc_s --pop-state \
-lc \
-lgcc \
/usr/lib/gcc-cross/x86_64-linux-gnu/15/crtendS.o \
/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crtn.o 
```
6. В результате получим файл, собранный с использованием нашего ld

Все это упражнение выше необходимо для того, чтобы иметь возможность сделать две вещи:
1) Отредактировать исходники ld для добавления вывода;
2) Дебажить ld (можно с использованием gdb, можно через vscode).

lunch.json для VSCode (могут отличаться названия утилит, опции такие же как и при выводе strace):

```
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug ld-new (build-id)",
      "type": "cppdbg",
      "request": "launch",
      "program": "${workspaceFolder}/build-gdb/ld/ld-new",
      "args": [
        "-plugin", "/usr/libexec/gcc-cross/x86_64-linux-gnu/15/liblto_plugin.so",
        "-plugin-opt=/usr/libexec/gcc-cross/x86_64-linux-gnu/15/lto-wrapper",
        "-plugin-opt=-fresolution=/tmp/ccKerzZh.res",
        "-plugin-opt=-pass-through=-lgcc",
        "-plugin-opt=-pass-through=-lgcc_s",
        "-plugin-opt=-pass-through=-lc",
        "-plugin-opt=-pass-through=-lgcc",
        "-plugin-opt=-pass-through=-lgcc_s",
        "--sysroot=/",
        "--build-id",
        "--eh-frame-hdr",
        "-m", "elf_x86_64",
        "--hash-style=gnu",
        "--as-needed",
        "--dynamic-linker", "/lib64/ld-linux-x86-64.so.2",
        "-pie",
        "-o checker_checked_debug_learn",
        "/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/Scrt1.o",
        "/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crti.o",
        "/usr/lib/gcc-cross/x86_64-linux-gnu/15/crtbeginS.o",
        "-L/usr/lib/gcc-cross/x86_64-linux-gnu/15",
        "-L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib",
        "-L/lib/x86_64-linux-gnu",
        "-L/lib/../lib",
        "-L/usr/lib/x86_64-linux-gnu",
        "-L/usr/lib/../lib",
        "-L/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib",
        "-L/lib",
        "-L/usr/lib",
        "[СЮДА ПУТЬ ДО ОБЪЕКТНОГО ФАЙЛА]",
        "-lgcc",
        "--push-state", "--as-needed", "-lgcc_s", "--pop-state",
        "-lc",
        "-lgcc",
        "/usr/lib/gcc-cross/x86_64-linux-gnu/15/crtendS.o",
        "/usr/lib/gcc-cross/x86_64-linux-gnu/15/../../../../x86_64-linux-gnu/lib/../lib/crtn.o"
      ],
      "cwd": "${workspaceFolder}",
      "MIMode": "gdb",
      "miDebuggerPath": "/usr/bin/gdb",
      "stopAtEntry": false,
      "externalConsole": false
    }
  ]
}
```

## Исследование исходников ld
В ходе анализа исходников были определены функции, которые отвечают за генерацию build-id:
1) generate_build_id (binutils-2.45.50.20251209/ld/ldbuildid.c) определяет "стиль" build-id;
интересующий нас кусок кода на момент написать данного решения
```
  else if (streq (style, "sha1"))
    {
      struct sha1_ctx ctx;

      sha1_init_ctx (&ctx);
      if (!(*checksum_contents) (abfd, (sum_fn) sha1_choose_process_bytes (),
				 &ctx))
	return false;
      sha1_finish_ctx (&ctx, id_bits);
    }
```
вызов функции generate_build_id (binutils-2.45.50.20251209/ld/ldelf.c):
```
  generate_build_id (abfd, style, bed->s->checksum_contents, id_bits, size);
```
*checksum_contents -- указатель на функцию, которая будет вызвана для создания build-id
2) elf_checksum_contents  -- функция, на которую указывает *checksum_contents, в ней реализуется логика обхода elf и добавление информации для получения sha1

код фукнции на момент написания (в коде добавлены кастомные функции для отладки, после добавления своего кода пересоберите бинарник как описано выше), комментарии сгенерированы автоматически:

```
bool
elf_checksum_contents (bfd *abfd,
		       void (*process) (const void *, size_t, void *),
		       void *arg)
{
  /*
   * abfd   — BFD-дескриптор ELF-файла
   * process — функция, которая "скармливает" байты в хэш
   *           (в нашем случае это sha1_process_bytes)
   * arg     — контекст SHA-1 (struct sha1_ctx)
   *
   * Эта функция НЕ вычисляет SHA-1 сама.
   * Она лишь перечисляет байты ELF в строго определённом порядке.
   */

  Elf_Internal_Ehdr *i_ehdrp = elf_elfheader (abfd);
  Elf_Internal_Shdr **i_shdrp = elf_elfsections (abfd);
  Elf_Internal_Phdr *i_phdrp = elf_tdata (abfd)->phdr;
  unsigned int count, num;

  /*
   * === 1. ELF HEADER ===
   *
   * В build-id участвует ELF header во ВНЕШНЕМ формате (как в файле),
   * но с важным отличием:
   *
   *   e_phoff и e_shoff обнуляются.
   *
   * Это сделано для того, чтобы build-id не зависел от смещений таблиц
   * в итоговом ELF-файле.
   */
  {
    Elf_External_Ehdr x_ehdr;
    Elf_Internal_Ehdr i_ehdr;

    /* Берём копию внутреннего заголовка */
    i_ehdr = *i_ehdrp;

    /* Обнуляем смещения таблиц */
    i_ehdr.e_phoff = i_ehdr.e_shoff = 0;

    /* Преобразуем во внешний (on-disk) формат */
    elf_swap_ehdr_out (abfd, &i_ehdr, &x_ehdr);

    /* Передаём байты ELF header в SHA-1 */
    (*process) (&x_ehdr, sizeof x_ehdr, arg);

    /* Отладочная точка: состояние SHA-1 после ELF header */
    _print_sha1_checkpoint ("EHDR", arg);
  }

  /*
   * === 2. PROGRAM HEADERS (PHDR) ===
   *
   * Хэшируются ВСЕ program headers, один за другим,
   * во внешнем формате, без каких-либо изменений.
   */
  num = i_ehdrp->e_phnum;
  for (count = 0; count < num; count++)
    {
      Elf_External_Phdr x_phdr;

      /* Преобразуем internal → external */
      elf_swap_phdr_out (abfd, &i_phdrp[count], &x_phdr);

      /* Передаём PHDR в SHA-1 */
      (*process) (&x_phdr, sizeof x_phdr, arg);

      /* Отладка: состояние SHA-1 после каждого PHDR */
      _print_sha1_checkpoint ("PHDRs", arg);
    }

  /*
   * === 3. SECTION HEADERS + CONTENTS ===
   *
   * Для КАЖДОЙ секции:
   *   1) хэшируется section header
   *   2) затем, при наличии, хэшируется содержимое секции
   */
  num = elf_numsections (abfd);
  for (count = 0; count < num; count++)
    {
      Elf_Internal_Shdr i_shdr;
      Elf_External_Shdr x_shdr;
      bfd_byte *contents, *free_contents;
      asection *sec = NULL;

      /* Берём копию section header */
      i_shdr = *i_shdrp[count];

      /*
       * КРИТИЧЕСКИЙ МОМЕНТ:
       *   sh_offset обнуляется перед хэшированием.
       *
       * Это означает, что build-id НЕ зависит от того,
       * где именно секция лежит в файле.
       */
      i_shdr.sh_offset = 0;

      /* Преобразуем header во внешний формат */
      elf_swap_shdr_out (abfd, &i_shdr, &x_shdr);

      /* Хэшируем section header */
      (*process) (&x_shdr, sizeof x_shdr, arg);
      _print_sha1_checkpoint ("SHDRs", arg);

      /*
       * === CONTENTS ===
       *
       * Теперь — содержимое секции, если оно существует.
       */

      /* SHT_NOBITS (например .bss) — содержимого нет */
      if (i_shdr.sh_type == SHT_NOBITS)
	continue;

      free_contents = NULL;
      contents = i_shdr.contents;

      /*
       * Если содержимое ещё не загружено —
       * BFD пытается получить его через asection.
       * Как понял автор, то это невозможно реализовать имея на руках только elf файл, 
       * поэтому в скрипте на питоне немного другие проверки(выведены путем дебага) для решения хэшировать содержимое секции или нет
       */
      if (contents == NULL)
	{
	  sec = bfd_section_from_elf_index (abfd, count);
	  if (sec != NULL)
	    {
	      contents = sec->contents;
	      if (contents == NULL)
		{
		  /* Принудительно читаем из файла */
		  sec->flags &= ~SEC_IN_MEMORY;
		  if (!_bfd_elf_mmap_section_contents (abfd, sec, &free_contents))
		    continue;
		  contents = free_contents;
		}
	    }
	}

      /*
       * Если содержимое удалось получить —
       * оно передаётся в SHA-1 ровно как есть.
       *
       * Именно здесь участвуют байты секции .text,
       * в том числе те, которые были затёрты в задании.
       */
      if (contents != NULL)
	{
	  (*process) (contents, i_shdr.sh_size, arg);
	  _print_sha1_checkpoint ("SHDRscont", arg);

	  /* Освобождаем mmap, если использовался */
	  _bfd_elf_munmap_section_contents (sec, free_contents);
	}
    }

  return true;
}
```
Таким образом, build-id вычисляется как SHA-1 от строго определённого потока байт:

1. ELF header (с обнулёнными e_phoff и e_shoff);
2. всех program headers;
3. всех section headers (с обнулённым sh_offset);
4. содержимого секций, за исключением следующих моментов:
    1. содержимое секций с типом SHT_NOBITS пропускаем;
    2. секции с размером 0 пропускаем;
    3. содержимое секции с именем .note.gnu.build-id зануляем целиком;
    4. содержимое секций с названиями ".strtab", ".shstrtab", ".symtab" пропускаем (может зависеть от версии binutils).

Затёртые байты в секции .text напрямую участвуют в этом потоке, что делает возможным их восстановление путём перебора значений и сравнения итогового build-id с имеющимся.

## Скрипт для решения
В результате отладки исходников ld и написания "аналогичного" алгоритма на Python получаем следюущий скрипт на питоне для вычисления неизвестных байт:

```
import hashlib
import struct
import sys
from dataclasses import dataclass
from typing import List, Optional, Tuple

# Your task-specific unknown bytes
UNKNOWN_FILE_OFF = 0x11E9
UNKNOWN_LEN = 8

# ELF constants (only what we need)
EI_CLASS = 4
EI_DATA = 5
ELFCLASS64 = 2
ELFDATA2LSB = 1

SHT_NOBITS = 8
SHT_NOTE = 7

NT_GNU_BUILD_ID = 3

def u16(b, o): return struct.unpack_from("<H", b, o)[0]
def u32(b, o): return struct.unpack_from("<I", b, o)[0]
def u64(b, o): return struct.unpack_from("<Q", b, o)[0]

def align4(x: int) -> int:
    return (x + 3) & ~3

def print_hex_rows(data: bytes, row=16):
    for i in range(0, len(data), row):
        chunk = data[i:i+row]
        print(f"{i:08x}: " + " ".join(f"{b:02x}" for b in chunk))

@dataclass
class Ehdr64:
    e_ident: bytes
    e_type: int
    e_machine: int
    e_version: int
    e_entry: int
    e_phoff: int
    e_shoff: int
    e_flags: int
    e_ehsize: int
    e_phentsize: int
    e_phnum: int
    e_shentsize: int
    e_shnum: int
    e_shstrndx: int

    def pack_external(self, zero_phoff_shoff: bool = False) -> bytes:
        # ELF64_Ehdr layout (little-endian)
        phoff = 0 if zero_phoff_shoff else self.e_phoff
        shoff = 0 if zero_phoff_shoff else self.e_shoff
        return struct.pack(
            "<16sHHIQQQIHHHHHH",
            self.e_ident,
            self.e_type,
            self.e_machine,
            self.e_version,
            self.e_entry,
            phoff,
            shoff,
            self.e_flags,
            self.e_ehsize,
            self.e_phentsize,
            self.e_phnum,
            self.e_shentsize,
            self.e_shnum,
            self.e_shstrndx,
        )

@dataclass
class Phdr64:
    p_type: int
    p_flags: int
    p_offset: int
    p_vaddr: int
    p_paddr: int
    p_filesz: int
    p_memsz: int
    p_align: int

    def pack_external(self) -> bytes:
        # ELF64_Phdr layout
        return struct.pack("<IIQQQQQQ",
            self.p_type,
            self.p_flags,
            self.p_offset,
            self.p_vaddr,
            self.p_paddr,
            self.p_filesz,
            self.p_memsz,
            self.p_align,
        )

@dataclass
class Shdr64:
    sh_name: int
    sh_type: int
    sh_flags: int
    sh_addr: int
    sh_offset: int
    sh_size: int
    sh_link: int
    sh_info: int
    sh_addralign: int
    sh_entsize: int

    def pack_external(self, zero_offset: bool = False) -> bytes:
        off = 0 if zero_offset else self.sh_offset
        # ELF64_Shdr layout
        return struct.pack("<IIQQQQIIQQ",
            self.sh_name,
            self.sh_type,
            self.sh_flags,
            self.sh_addr,
            off,
            self.sh_size,
            self.sh_link,
            self.sh_info,
            self.sh_addralign,
            self.sh_entsize,
        )

def parse_ehdr64(data: bytes) -> Ehdr64:
    if data[:4] != b"\x7fELF":
        raise ValueError("Not an ELF file")
    if data[EI_CLASS] != ELFCLASS64:
        raise ValueError("Not ELF64")
    if data[EI_DATA] != ELFDATA2LSB:
        raise ValueError("Not little-endian")

    e_ident = data[:16]
    # Offsets from ELF64 spec
    e_type      = u16(data, 0x10)
    e_machine   = u16(data, 0x12)
    e_version   = u32(data, 0x14)
    e_entry     = u64(data, 0x18)
    e_phoff     = u64(data, 0x20)
    e_shoff     = u64(data, 0x28)
    e_flags     = u32(data, 0x30)
    e_ehsize    = u16(data, 0x34)
    e_phentsize = u16(data, 0x36)
    e_phnum     = u16(data, 0x38)
    e_shentsize = u16(data, 0x3A)
    e_shnum     = u16(data, 0x3C)
    e_shstrndx  = u16(data, 0x3E)

    return Ehdr64(
        e_ident, e_type, e_machine, e_version, e_entry, e_phoff, e_shoff,
        e_flags, e_ehsize, e_phentsize, e_phnum, e_shentsize, e_shnum, e_shstrndx
    )

def parse_phdrs64(data: bytes, eh: Ehdr64) -> List[Phdr64]:
    phdrs = []
    for i in range(eh.e_phnum):
        off = eh.e_phoff + i * eh.e_phentsize
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = struct.unpack_from(
            "<IIQQQQQQ", data, off
        )
        phdrs.append(Phdr64(p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align))
    return phdrs

def parse_shdrs64(data: bytes, eh: Ehdr64) -> List[Shdr64]:
    shdrs = []
    for i in range(eh.e_shnum):
        off = eh.e_shoff + i * eh.e_shentsize
        sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size, sh_link, sh_info, sh_addralign, sh_entsize = struct.unpack_from(
            "<IIQQQQIIQQ", data, off
        )
        shdrs.append(Shdr64(
            sh_name, sh_type, sh_flags, sh_addr, sh_offset, sh_size,
            sh_link, sh_info, sh_addralign, sh_entsize
        ))
    return shdrs

def get_section_names(data: bytes, eh: Ehdr64, shdrs: List[Shdr64]) -> List[str]:
    # Read section header string table
    shstr = shdrs[eh.e_shstrndx]
    blob = data[shstr.sh_offset: shstr.sh_offset + shstr.sh_size]

    names = []
    for sh in shdrs:
        start = sh.sh_name
        end = blob.find(b"\x00", start)
        if end == -1:
            names.append("")
        else:
            names.append(blob[start:end].decode(errors="replace"))
    return names

def find_buildid_desc_by_section(data: bytes, shdrs: List[Shdr64], names: List[str]) -> Tuple[int, int]:
    """
    Find .note.gnu.build-id as a section (SHT_NOTE) and parse its notes to locate
    (file_offset_of_desc, desc_size) for NT_GNU_BUILD_ID with name "GNU".
    """
    for sh, nm in zip(shdrs, names):
        if nm != ".note.gnu.build-id":
            continue
        if sh.sh_type != SHT_NOTE:
            # still try, but normally it is SHT_NOTE
            pass
        blob = data[sh.sh_offset: sh.sh_offset + sh.sh_size]
        i = 0
        n = len(blob)
        while i + 12 <= n:
            namesz, descsz, ntype = struct.unpack_from("<III", blob, i)
            i += 12
            name_start = i
            name_end = name_start + namesz
            if name_end > n:
                break
            name = blob[name_start:name_end].rstrip(b"\x00")
            i = align4(name_end)

            desc_start = i
            desc_end = desc_start + descsz
            if desc_end > n:
                break
            i = align4(desc_end)

            if name == b"GNU" and ntype == NT_GNU_BUILD_ID:
                return sh.sh_offset + desc_start, descsz

    raise RuntimeError("Could not find NT_GNU_BUILD_ID desc inside .note.gnu.build-id section")

def read_stored_buildid(data: bytes, shdrs: List[Shdr64], names: List[str]) -> bytes:
    off, sz = find_buildid_desc_by_section(data, shdrs, names)
    return data[off:off+sz]

def get_prefix_suffix_preprocessed_like_ld(data: bytes):
    # парсим ELF header, program headers, section headers, имена секций
    eh = parse_ehdr64(data)
    phdrs = parse_phdrs64(data, eh)
    shdrs = parse_shdrs64(data, eh)
    names = get_section_names(data, eh, shdrs)

    prefix_parts = []
    suffix_parts = []

    # ld хэширует EHDR, но e_phoff/e_shoff = 0
    prefix_parts.append(eh.pack_external(zero_phoff_shoff=True))

    # затем ld хэширует все PHDR
    for ph in phdrs:
        prefix_parts.append(ph.pack_external())

    # неизвестный диапазон в файле: [u0, u1)
    u0 = UNKNOWN_FILE_OFF
    u1 = UNKNOWN_FILE_OFF + UNKNOWN_LEN

    # переменная определяет, прошли ли мы неизвестные байты в потоке данных
    # В задаче диапазон unknown лежит внутри .text, поэтому переключатель срабатывает в одном месте
    unknown_bytes_passed = False

    # далее ld идёт по заголовкам секций и содержимому секций
    for i, sh in enumerate(shdrs):
        sec_start = sh.sh_offset
        sec_end = sh.sh_offset + sh.sh_size

        # SHDR всегда идёт в потоке до contents этой секции,
        # поэтому до unknown кладём в prefix, после — в suffix
        if unknown_bytes_passed:
            suffix_parts.append(sh.pack_external(zero_offset=True))
        else:
            prefix_parts.append(sh.pack_external(zero_offset=True))

        # пропускаем секции без данных в файле или нулевого размера
        if sh.sh_type == SHT_NOBITS or sh.sh_size == 0:
            continue

        # эти секции в задаче не учитывались при воспроизведении ld
        if names[i] in (".strtab", ".shstrtab", ".symtab"):
            continue

        # .note.gnu.build-id полностью зануляется при хэшировании
        if names[i] == ".note.gnu.build-id" and sh.sh_type == SHT_NOTE:
            sec = b"\x00" * sh.sh_size
        else:
            sec = data[sec_start:sec_end]

        # разрезаем contents секции, если unknown лежит внутри неё: до начала неизвестных байт кладем в префикс, после конца неизвестных байт -- в суффикс
        if sec_start <= u0 and u1 <= sec_end:
            prefix_parts.append(sec[:u0 - sec_start])     # до unknown
            suffix_parts.append(sec[u1 - sec_start:])     # после unknown
            unknown_bytes_passed = True
        else:
            # секция целиком до unknown
            if sec_end <= u0:
                prefix_parts.append(sec)
            # секция целиком после unknown
            elif sec_start >= u1:
                suffix_parts.append(sec)

    return b"".join(prefix_parts), b"".join(suffix_parts)

def brute_unknown_fast(prefix, suffix, target_hex, alphabet: bytes, unknown_len=8):
    import hashlib, itertools
    target = bytes.fromhex(target_hex)

    h_prefix = hashlib.sha1() 
    h_prefix.update(prefix)
    tested = 0
    for tup in itertools.product(alphabet, repeat=unknown_len):
        h = h_prefix.copy()
        h.update(bytes(tup))   
        h.update(suffix)
        tested += 1
        if tested % 5_000_000 == 0:
            print("tested", tested)
        if h.digest() == target:
            return bytes(tup)
    return None

def main(path: str, mode: str="", candidate: Optional[str] = None):
    raw = open(path, "rb").read()

    eh = parse_ehdr64(raw)
    shdrs = parse_shdrs64(raw, eh)
    names = get_section_names(raw, eh, shdrs)

    stored = read_stored_buildid(raw, shdrs, names)
    print("Stored Build ID (from file):", stored.hex())


    prefix, suffix = get_prefix_suffix_preprocessed_like_ld(raw)
    alphabet =b"0123456789abcdef"
    result = brute_unknown_fast(prefix, suffix, stored.hex(), alphabet, 8)
    print(result)
    return

if __name__ == "__main__":
    path = sys.argv[1]
    main(path)

```

### Запуск скрипта
```
python3 flag_checker/solution_final.py  'flag_checker/censored_checker_5436028.elf'
Stored Build ID (from file): eeb1c4e54c7adc376da8365448d43331de23fb18
tested 5000000
tested 10000000
tested 15000000
...
tested 4030000000
tested 4035000000
tested 4040000000
tested 4045000000
tested 4050000000
tested 4055000000
b'f1eddc5d'
```