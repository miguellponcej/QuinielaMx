# QuinielaPredictor MX

Aplicacion experta para analisis probabilistico, optimizacion de boletos y simulacion de quinielas de Loteria Nacional mexicana, con foco en Progol, Progol Revancha, Progol Media Semana y Protouch.

## Aviso importante

Este proyecto no garantiza premios ni resultados. Los juegos deportivos tienen incertidumbre real y los sorteos aleatorios puros no tienen memoria estadistica confiable para prediccion causal. El objetivo es maximizar probabilidad estimada, cobertura inteligente, control de costo y valor esperado cuando existan datos suficientes.

## Capacidades

- Configuracion parametrizable para Progol, Revancha, Media Semana y Protouch.
- Consulta web/cache de quinielas vigentes sin solicitar cargas al usuario.
- Modelos base: Elo, Poisson soccer, aproximacion Dixon-Coles, NFL por margen/spread, ensamble y calibracion.
- Optimizacion de boletos con fijos, dobles y triples bajo presupuesto.
- Estrategias de bajo costo: economico, balanceado, agresivo y personalizado.
- Seleccion marginal de coberturas por entropia, brecha top1-top2, costo marginal, beneficio probabilistico marginal y ratio beneficio/costo.
- Simulacion Monte Carlo de escenarios.
- Backtesting con accuracy, log loss, Brier score y ROI simulado.
- Analisis descriptivo de sorteos aleatorios sin prometer prediccion causal.
- Interfaz Streamlit con dashboard, prediccion, optimizacion, simulacion e historicos.
- Home privado con consulta de sorteos/quinielas vigentes, cache, logs y recomendaciones automaticas por juego.
- Pipeline auditado `real_time_prediction_pipeline()` para que los flujos de app generen predicciones solo con trazabilidad de fuentes.
- Carga local de `.env` para ejecucion privada en escritorio sin exponer secretos en el codigo.

## Instalacion

```bash
cd quiniela_predictor_mx
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Ejecutar la app

Primero configura `.env` a partir de `.env.example`. La app carga ese archivo localmente y mantiene prioridad para variables ya definidas en el entorno.

```bash
streamlit run app/streamlit_app.py --server.address 127.0.0.1 --server.port 8501
```

En Windows tambien puedes usar el lanzador seguro, que solicita la contrasena sin guardarla en texto plano:

```powershell
powershell -ExecutionPolicy Bypass -File .\infra\scripts\start_local_app.ps1
```

La app siempre pide login antes de mostrar Home.

## Ejecutar pruebas

```bash
pytest
```

## Streamlit Community Cloud

La app esta preparada para publicarse en Streamlit Community Cloud:

```text
Repository: miguellponcej/QuinielaMx
Branch: main
Main file path: app/streamlit_app.py
```

Configura los secretos desde el panel privado de Streamlit Cloud usando
`.streamlit/secrets.example.toml` como plantilla. Consulta `STREAMLIT_CLOUD.md`
para los pasos completos.

## Datos de ejemplo para pruebas internas

- `data/examples/progol_quiniela.csv`
- `data/examples/protouch_quiniela.csv`
- `data/examples/random_draws_melate.csv`
- `data/examples/match_results_soccer.csv`
- `data/examples/nfl_results.csv`
- `data/examples/progol_backtest_sample.csv`
- `data/examples/progol_historical_results_long.csv`

Los datos reales de operacion deben venir de fuentes web oficiales/configuradas y cache local. Los archivos de ejemplo son solo para pruebas automatizadas y desarrollo.

## Plantillas internas opcionales

Las plantillas Excel estan en `data/templates` para auditoria interna o pruebas controladas. El flujo normal de usuario no solicita carga manual:

- `plantillas_captura_manual.xlsx`: libro unico con todas las hojas.
- `quiniela_progol.xlsx`
- `quiniela_protouch.xlsx`
- `probabilidades_mercado_progol.xlsx`
- `probabilidades_mercado_protouch.xlsx`
- `resultados_soccer.xlsx`
- `resultados_nfl_ncaa.xlsx`
- `historico_progol.xlsx`
- `historico_protouch.xlsx`

Para regenerarlas:

```bash
python scripts/create_templates.py
```

## Actualizacion semiautomatica

El flujo de usuario es web-only: la interfaz no solicita archivos manuales. El sistema consulta fuentes oficiales/configuradas, usa cache local y registra diagnostico por fuente. Las plantillas y conectores locales quedan solo para pruebas internas, auditoria y mantenimiento tecnico.

Fuentes configuradas:

- Oficiales: Pronosticos/Loteria Nacional para Progol, Progol Media Semana, Protouch y resultados.
- Canal autorizado: TuLotero Mexico para contrastar vigencia, concurso, premio/costo cuando el contenido sea publico.
- Casas de apuestas: Caliente, bet365, Codere, Betcris y Betsson como referencias de mercado bajo acceso permitido.
- APIs estructuradas: The Odds API, Odds-API.io, football-data.org, API-Football y SportsGameOdds cuando se configuren claves.

Variables opcionales para APIs:

```text
THE_ODDS_API_KEY=
ODDS_API_IO_KEY=
FOOTBALL_DATA_API_KEY=
API_FOOTBALL_KEY=
SPORTS_GAME_ODDS_API_KEY=
```

Las casas de apuestas pueden usar paginas dinamicas, geobloqueo, sesion o restricciones de terminos. Si una fuente no responde, bloquea o exige clave, la app lo registra en el panel "Estado de fuentes web" y pasa a la siguiente fuente/cache. No se inventan partidos, momios, fechas ni premios.

Conectores internos disponibles para mantenimiento tecnico:

- Resultados historicos de futbol soccer.
- Resultados historicos NFL/NCAA.
- Probabilidades de mercado cuando esten disponibles en fuente web estructurada.
- Quinielas actuales Progol/Protouch.
- Historicos oficiales Progol, Revancha y Protouch.

Las validaciones revisan equipos local/visitante, suma de probabilidades, numero de partidos del juego seleccionado, presupuesto disponible y calculo correcto del costo.

## Backtesting comparativo

La pantalla de Historicos y el modulo `src.backtesting` comparan el desempeno contra:

- Siempre local.
- Favorito de mercado.
- Frecuencia historica.
- Aleatorio.
- Elo.
- Ensamble.

## Formato esperado de quiniela Progol

```json
[
  {
    "id": 1,
    "local": "Equipo A",
    "visitante": "Equipo B",
    "liga": "Liga MX",
    "fecha": "2026-05-10"
  }
]
```

## Formato esperado de quiniela Protouch

```json
[
  {
    "id": 1,
    "local": "Equipo A",
    "visitante": "Equipo B",
    "liga": "NFL",
    "fecha": "2026-09-10"
  }
]
```

## Flujo recomendado

1. Iniciar sesion con usuario autorizado.
2. Abrir Home para ejecutar `load_active_draws_home_dashboard()`.
3. Revisar tarjetas de juegos vigentes, datos faltantes y recomendaciones.
4. Actualizar fuentes web/cache si la fuente oficial no expone datos estructurados.
5. Generar predicciones.
6. Optimizar boleto con presupuesto y perfil de riesgo.
7. Simular 100,000 escenarios.
8. Guardar resultados para backtesting futuro.

## Home inteligente

La pantalla Home consulta fuentes oficiales/configuradas, valida frescura, usa cache si no hay internet y muestra:

- Total de juegos encontrados.
- Quinielas deportivas.
- Sorteos aleatorios.
- Juegos recomendados.
- Datos incompletos.
- Centro de decision con juegos listos para predecir, juegos que requieren mas datos web, mejor calidad de datos y proximo cierre.
- Tabla priorizada para ver que analizar primero, calidad de datos, accion sugerida y si existe prediccion directa.
- Tarjetas por juego con score, calidad de datos, premio/bolsa, costo, accion sugerida y estado de prediccion directa.
- Panel de estado de fuentes web con fuentes oficiales, TuLotero, casas de apuestas y APIs de momios, incluyendo si respondieron, si requieren clave o si no entregaron contenido util.
- Ejecucion de prediccion desde Home cuando la quiniela deportiva ya tiene partidos estructurados y el usuario esta autenticado.

Los sorteos aleatorios se marcan como informativos. El sistema no predice numeros ganadores.

Configuracion:

```text
ACTIVE_DRAWS_REFRESH_MINUTES=60
```

Cache y logs:

```text
data/active_draws/cache/
data/active_draws/logs/
data/active_draws/snapshots/
```

## Regla de trazabilidad obligatoria

El motor bloquea cualquier prediccion que no reciba un contexto de trazabilidad (`PredictionTrace`).
Los flujos de la interfaz usan `src.realtime.real_time_prediction_pipeline.real_time_prediction_pipeline()` como entrada auditada para predicciones y optimizacion.
Cada corrida debe registrar:

- Archivos internos usados.
- Fuentes web consultadas o registradas para verificacion.
- Datos actualizados.
- Datos incompletos.
- Datos descartados.
- Variables que alimentaron el modelo.
- Version del modelo y fecha/hora de la prediccion.

La salida se trata como una decision probabilistica bajo incertidumbre, nunca como certeza.

## Escenarios de optimizacion

- Economico: minimo costo, maximo 3 dobles y 0 triples; solo cubre partidos con alta incertidumbre.
- Balanceado: mejor relacion probabilidad/costo; usa dobles en partidos cerrados y maximo 1 triple si la incertidumbre es extrema.
- Agresivo: mayor cobertura bajo presupuesto; prioriza partidos con probabilidades muy cercanas.
- Personalizado: el usuario define presupuesto maximo y el sistema decide automaticamente cuantos dobles y triples usar.

El algoritmo ordena coberturas por beneficio probabilistico marginal por peso invertido, no por intuicion ni al azar.
