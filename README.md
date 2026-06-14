# Cart-ON
Robot asistente guía.

## Índice del projecto
- [Descripción](#Descripción)
- [Arquitectura Tecnológica](#Arquitectura-Tecnológica)
- [Software](#Software)
- [Componentes Hardware](#Componentes-Hardware)
- [Diseño 3D](#Diseño-3D)
- [Enlaces](#Enlaces)
- [Instalacion] (#Instalacion)
- [Miembros del equipo](#Miembros-del-equipo)

## Descripción
Este proyecto consiste en el desarrollo de un robot guia autónomo diseñado para la orientación en espacios interiores complejos, como supermercados y centros educativos. El robot interactúa con el usuario mediante comandos de voz, procesa la solicitud y guía a la persona hasta el destino u objeto deseado de forma segura y eficiente.

## Arquitectura Tecnológica
- SLAM (Simultaneous Localization and Mapping):
Utilizamos algoritmos de SLAM para que el robot construya un mapa del entorno mientras calcula su propia posición. Esto se logra mediante un sensor de distancia (LiDAR), permitiendo una navegación precisa en diferentes escenarios.

- Visión Artificial y Reconocimiento de Objetos:
Una vez el terreno es conocido, el sistema emplea modelos de Computer Vision para diferenciar objetos o productos. Esto permite que el robot no solo sepa donde esta la fruta, sino también que tipo de fruta hay.

- Procesamiento de Lenguaje y Voz (Cloud Services):
  - Speech-to-Text (STT): Captura del audio ambiental para convertir la voz del usuario en texto procesable mediante servicios en la nube.
  - Text-to-Speech (TTS): Generación de una respuesta vocal para que el robot confirme el destino o interactúe con el usuario.

## Software

![Diagrama de capas](documentos/diagramas/diagrama_capas.jpeg)

## Componentes Hardware

| Componente | Especificación Técnica | Cantidad |
| :--- | :--- | :---: |
| **Cámara** | Raspberry Pi Camera Module v1.3 (5 MP, Sensor OmniVision OV5647) | 1 |
**Sensor LiDAR** | Slamtec RPLIDAR C1 (Escaneo 2D de 360°, alcance de 12m, tecnología DToF) | 1 |
| **Micrófono** | MillSO Mini Micrófono USB para PC (Omnidireccional, plug-and-play, captación de voz) | 1 |
| **Altavoces** | Altavoces genéricos USB (Alimentación USB de 5V con entrada de audio por conector Jack de 3.5mm) | 1 |
| **Pantallas Ojos** | Pantalla OLED 1.3" (Resolución 128x64, Controlador SSH1106, interfaz I2C) | 2 |
| **Pantalla Central** | LILYGO T5 4.7" S3 E-paper (Pantalla de tinta electrónica, SoC ESP32-S3, resolución 960x540) | 1 |
| **Batería Lipo** | Batería Zaaa 2S (7.4V, 5200mAh, tasa de descarga de 50C, 38.48 Wh) | 1 |
| **Power Bank** | CUKTECH 15 Power Bank (20000mAh, carga rápida bidireccional de hasta 150W MAX) | 1 |
| **SBC** | Raspberry Pi 4 Model B (Procesador Quad-core a 1.5GHz, 4GB de memoria RAM LPDDR4) | 1 |
| **Microcontrolador** | Arduino Uno Rev3 | 1 |
| **Motores de Tracción** | Motor DC Globe Motors 12V (Model: 455A1016) | 2 |
| **Encóderes Rotativos** | Encóder óptico incremental US Digital (Serie E5) | 2 |
| **Ruedas** | Ruedas genéricas antipinchazos 15 cm de diámetro| 2 |
| **Caster Wheels**| Ruedas locas genéricas 6 cm de diámetro | 2 |

## Diseño 3D

![3DCUERPO](documentos/3D_CUERPO.jpeg)



## Enlaces:
<a href="https://docs.google.com/document/d/17ys1AdFQXFy2MDise_eSwjZ4mOGR0Uw6nk950iQLUHs/edit?usp=sharing" target="_blank">Documento de Especificación de Requisitos del Sistema</a>

<a href="https://docs.google.com/spreadsheets/d/1p9h1Z-hoTksufFietCflG6-x_P8x_Dwd/edit?gid=2124654508#gid=2124654508" target="_blank">Presupuesto Componentes del Robot</a>

## Instalacion:

Prerrequisitos:
- ROS 2 Jazzy

Paquetes ROS necesarios:
- rclpy
- sensor_msgs
- nav_msgs

Cada vez que se inicia el entorno Ubuntu:
source /opt/ros/jazzy/setup.bash

## Miembros del equipo:
- Daniel Cruz Flores. NIU 1709912
- Felipe Marcano Hurtado. NIU 1635636
- Marc Solés i Rojas. NIU 1710741
- Marco Mejías Alés. NIU 1710748
- Samuel Jesus Outeda Aponte. NIU 1711378
