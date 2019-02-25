OCT software
============

To do
-----

1.	Organizar como librería de Python (!)
2.	[Buffer] Debería incluír el contenedor de datos (un array Data de numpy)
3.	[Buffer] El índice del buffer es, en realidad, el índice para las operaciones tipo set. Debería haber un análogo para operaciones tipo get (con sus respectivos índices) que permitan implementar funcionalidades tipo FIFO o LIFO.
4.	[SpectraAnalyzer] Filtro tipo boxcar
5.	[SpectraAnalyzer] ROI independiente
6.	[SpectraAnalyzerUi] Settear calibraciones (abrir una ventana)
7.	[SpectraSave] Incorporar opción para guardado de único archivo y que sea la opción por defecto (luego borrar la sección de guardado de SpectraAnalyzer)
				  Cambiar el checkbox "enable" por un botón tipo start/stop
				  Agregar alerta si ningún checkbox (processed, reference, dark, raw) está seleccionado
8.	Que los widgets de la barra lateral puedan expandirse/contraerse
9.	[CameraControl] Admitir tiempo de exposición automático a partir de evitar que la cámara sature
9.	[SpectraAnalyzer] Incluir monitor de timing (tiempo de adquisición, tiempo de procesado, overload, frames perdidos, etc.)