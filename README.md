# Projecte Cart-ON: Sistema Robòtic Assistent i Guia Autònom


**Cart-ON** es un Robot Mòbil Autònom (AMR) dissenyat per a l'assistència, orientació i guiatge en espais interiors complexos. El sistema integra navegació autònoma avançada, interacció natural mitjançant veu i models d'Intel·ligència Artificial generativa.

https://github.com/user-attachments/assets/891a531e-57d5-429f-b882-7a4eace39d10

---

## 📑 Índex del Projecte
1. [Descripció General i Casos d'Ús](#1-descripció-general-i-casos-dús)
2. [Arquitectura Tecnològica (Edge-Cloud)](#2-arquitectura-tecnològica-edge-cloud)
3. [Especificacions de Maquinari](#3-especificacions-de-maquinari)
4. [Disseny 3D i Mecànica](#4-disseny-3d-i-mecànica)
5. [Instal·lació i Desplegament](#5-instal·lació-i-desplegament)
6. [Procediment d'Execució](#6-procediment-dexecució)
7. [Enllaços d'Interès](#7-enllaços-dinterès)
8. [Equip de Desenvolupament](#8-equip-de-desenvolupament)

---

## 1. Descripció General i Casos d'Ús

L'objectiu principal de Cart-ON és assistir en la navegació i localització de productes o destinacions en espais qüotidians, oferint una experiència amigable. No només actua com un vehicle de guiatge físic, sinó com un assistent cognitiu multimodal, capaç d'entendre instruccions de veu en llenguatge natural, raonar sobre l'entorn i interactuar visualment i de forma auditiva amb l'usuari.

El sistema disposa d'una màquina d'estats lògica que permet operar en dos entorns principals:
* **Entorn Retail (Supermercat):** Proporciona funcionalitats de gestió de la llista d'anar a comprar, escaneig de prestatgeries mitjançant Visió per Computador per actualitzar l'inventari en temps real, i guiatge físic fins a la ubicació exacta dels productes.
* **Entorn Acadèmic (Campus Universitari):** Connectat a la base de dades de la UAB, el sistema processa consultes d'horaris, assignatures i aules, generant mapes visuals a la interfície i calculant la ruta òptima per guiar els estudiants.

---

## 2. Arquitectura Tecnològica (Edge-Cloud)

Per tal de garantir una resposta en temps real i evitar colls d'ampolla computacionals en el maquinari mòbil, l'arquitectura del programari s'ha dividit en un paradigma Edge-Cloud.

### 2.1. Capa Edge (Processament Local al Robot)
Aquesta capa s'executa a la placa principal (Raspberry Pi) i s'encarrega de les tasques crítiques de control, percepció immediata i maquinari:
* **Middleware ROS 2 (Jazzy):** Orquestra els nodes de comunicació entre sensors i actuadors.
* **Navegació i SLAM:** Mitjançant el sensor LiDAR (Slamtec RPLIDAR C1), el robot construeix mapes topològics 2D i calcula la seva odometria per evitar obstacles dinàmics de manera autònoma.
* **HRI (Human-Robot Interaction):** Gestió en temps real dels micròfons, síntesi de veu (TTS) i control de les interfícies gràfiques (pantalla E-ink principal i pantalles OLED per a l'expressivitat facial).

### 2.2. Capa Cloud (Processament Lògic i IA)
Aquesta capa externalitza la càrrega cognitiva a un servidor *Serverless* desplegat a **Google Cloud Run** mitjançant una API RESTful construïda amb FastAPI:
* **Processament de Llenguatge Natural (NLP):** S'integren crides a l'API dels models LLM (Qwen de la UAB) per traduir la veu de l'usuari a intencions estructurades (JSON) i generar respostes empàtiques.
* **Visió Artificial (VLM):** Processament d'imatges codificades en Base64 procedents de la càmera del robot per detectar productes, obtenir les *Bounding Boxes* i localitzar-los espacialment.
* **Persistència de Dades (MySQL):** Base de dades relacional que emmagatzema l'inventari geolocalitzat i els horaris acadèmics, resolent ambicions terminològiques (com les variacions entre català i castellà de les assignatures) mitjançant algorismes d'extracció d'arrels.

![Diagrama de capes](documentos/diagramas/diagrama_capas.jpeg)

---

## 3. Especificacions de Maquinari

El disseny de Cart-ON és modular, combinant components industrials amb electrònica de consum per optimitzar el cost sense sacrificar la precisió.

| Categoria | Component | Especificació Tècnica | Quantitat |
| :--- | :--- | :--- | :---: |
| **Unitat Central** | **SBC (Single Board Computer)** | Raspberry Pi 4 Model B (Processador Quad-core 1.5GHz, 4GB RAM LPDDR4) | 1 |
| **Control de Baix Nivell**| **Microcontrolador** | Arduino Uno Rev3 (Gestió directa de motors i sensors simples) | 1 |
| **Sensòrica i Percepció** | **Sensor LiDAR** | Slamtec RPLIDAR C1 (Escaneig 2D de 360°, abast de 12m, tecnologia DToF) | 1 |
| | **Càmera** | Raspberry Pi Camera Module v1.3 (5 MP, Sensor OmniVision OV5647) | 1 |
| | **Micròfon** | MillSO Mini Micròfon USB per a PC (Omnidireccional, plug-and-play) | 1 |
| **Interacció (HRI)** | **Pantalla Central** | LILYGO T5 4.7" S3 E-paper (Tinta electrònica, SoC ESP32-S3, resolució 960x540) | 1 |
| | **Pantalles Facials (Ulls)** | Pantalla OLED 1.3" (Resolució 128x64, Controlador SSH1106, bus I2C) | 2 |
| | **Altaveus** | Altaveus genèrics USB (Alimentació 5V, connector Jack 3.5mm) | 1 |
| **Locomoció i Tracció** | **Motors de Tracció** | Motor DC Globe Motors 12V (Model: 455A1016) | 2 |
| | **Encòders Rotatius** | Encòder òptic incremental US Digital (Sèrie E5) per a odometria precisa | 2 |
| | **Rodes Principals** | Rodes genèriques antipunxades (15 cm de diàmetre) | 2 |
| | **Rodes de Suport (Caster)** | Rodes boges genèriques (6 cm de diàmetre) | 2 |
| **Sistema Energètic** | **Bateria Lipo** | Bateria Zaaa 2S (7.4V, 5200mAh, taxa de descàrrega 50C, 38.48 Wh) | 1 |
| | **Power Bank** | CUKTECH 15 Power Bank (20000mAh, càrrega ràpida bidireccional fins a 150W MAX) | 1 |

---

## 4. Disseny 3D i Mecànica

El xassís de Cart-ON ha estat dissenyat per suportar la integració harmònica de tots els components electrònics, mantenint un centre de gravetat baix i oferint una estructura ergonòmica perquè els usuaris puguin llegir la pantalla E-ink amb facilitat.

![Visualització del disseny 3D](documentos/3D_CUERPO.jpeg)

---

## 5. Instal·lació i Desplegament

### 5.1. Prerequisits del Sistema Edge (Local)
L'entorn de desenvolupament principal requereix una distribució de Linux compatible amb l'ecosistema ROS.
* **Sistema Operatiu:** Ubuntu 24.04 LTS.
* **Middleware:** ROS 2 Jazzy.
* **Llenguatge:** Python 3.10 o superior.

**Paquets ROS 2 necessaris:**
Cal verificar la presència dels paquets bàsics d'orquestració de missatges:
* `rclpy`
* `sensor_msgs`
* `nav_msgs`

### 5.2. Configuració de l'Entorn Local
1. Clonació del repositori oficial: git clone [https://github.com/el-vostre-repositori/Cart-ON.git](https://github.com/el-vostre-repositori/Cart-ON.git)
  cd Cart-ON
2. Instal·lació de dependències de Python (entorn virtual recomanat):
  pip install -r requirements.txt
3. Incorporació de les variables d'entorn de ROS 2 al terminal actiu (aquesta acció s'ha de repetir cada cop que s'iniciï una nova sessió d'Ubuntu):
  source /opt/ros/jazzy/setup.bash
4. Execució carpeta ./source: python main.py

---

### 6. Equip de desenvolupament

Daniel Cruz Flores - NIU 1709912
Felipe Marcano Hurtado - NIU 1635636
Marc Solés i Rojas - NIU 1710741
Marco Mejías Alés - NIU 1710748
Samuel Jesus Outeda Aponte - NIU 1711378


  
