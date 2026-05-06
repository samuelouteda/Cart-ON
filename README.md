# Cart-ON
Robot asistente guía.

## Índice del projecto
- [Descripción](#Descripción)
- [Arquitectura Tecnológica](#Arquitectura-Tecnológica)
- [Software](#Software)
- [Componentes Hardware](#Componentes-Hardware)
- [Diseño 3D](#Diseño-3D)
- [Enlaces](#Enlaces)
- [Miembros del equipo](#Miembros-del-equipo)

## Descripción
Este proyecto consiste en el desarrollo de un robot guia autónomo diseñado para la orientación en espacios interiores complejos, como supermercados y centros educativos. El robot interactúa con el usuario mediante comandos de voz, procesa la solicitud y guía a la persona hasta el destino u objeto deseado de forma segura y eficiente.

## Arquitectura Tecnológica
- SLAM (Simultaneous Localization and Mapping):
Utilizamos algoritmos de SLAM para que el robot construya un mapa del entorno mientras calcula su propia posición. Esto se logra mediante la fusión de datos de una cámara (Visual SLAM) y un sensor de distancia (LiDAR y Ultrasonidos), permitiendo una navegación precisa en diferentes escenarios.

- Visión Artificial y Reconocimiento de Objetos:
Una vez el terreno es conocido, el sistema emplea modelos de Computer Vision para diferenciar objetos o productos. Esto permite que el robot no solo sepa donde esta la fruta, sino también que tipo de fruta hay.

- Procesamiento de Lenguaje y Voz (Cloud Services):
  - Speech-to-Text (STT): Captura del audio ambiental para convertir la voz del usuario en texto procesable mediante servicios en la nube.
  - Text-to-Speech (TTS): Generación de una respuesta vocal para que el robot confirme el destino o interactúe con el usuario.

## Software

## Componentes Hardware

## Diseño 3D

## Enlaces:
[Documento de Especificación de Requisitos del Sistema](https://docs.google.com/document/d/17ys1AdFQXFy2MDise_eSwjZ4mOGR0Uw6nk950iQLUHs/edit?usp=sharing)

[Presupuesto Componentes del Robot](https://docs.google.com/spreadsheets/d/1p9h1Z-hoTksufFietCflG6-x_P8x_Dwd/edit?gid=2124654508#gid=2124654508)

## Miembros del equipo:
- Daniel Cruz Flores. NIU 1709912
- Felipe Marcano Hurtado. NIU 1635636
- Marc Solés i Rojas. NIU 1710741
- Marco Mejías Alés. NIU 1710748
- Samuel Jesus Outeda Aponte. NIU 1711378
