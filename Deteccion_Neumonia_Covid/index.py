
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QMainWindow, QDialog, QLabel, QApplication, QFileDialog, QWidget, QMessageBox, QTableWidgetItem
from PyQt5.uic import loadUiType
import sys
import mysql.connector
import random
import datetime

from tensorflow.keras.models import load_model
import numpy as np
import skimage
from skimage.io import imread
from skimage.transform import resize
from skimage.color import rgb2gray
from xlsxwriter import Workbook


bd = mysql.connector.connect(
    host = '',
    user = '',
    password = '',
    database = ''
)
dbcursor = bd.cursor(buffered=True)

ui,_ = loadUiType('ventanas/deteccion-neumonia_covid.ui')
radiografia,_ = loadUiType('ventanas/ventana-radiografia.ui')
login,_ = loadUiType('login.ui')

# Cargar el modelo de la Red Neuronal Convolucional
rnc_model = load_model('modelo_rnc/rnc_model.h5')
rnc_model_covid = load_model('modelo_rnc/rnc_model_covid.h5')


"""
class Login(QWidget, login):

    def __init__(self):
        QWidget.__init__(self)
        self.setupUi(self)

        self.pushButton.clicked.connect(self.login)

        style = open('temas/darkorange.css', 'r')
        style = style.read()
        self.setStyleSheet(style)


    def login(self):
        usuario = self.lineEdit.text()
        password = self.lineEdit_2.text()

        sql = ''' SELECT * FROM doctor '''

        dbcursor.execute(sql)
        dato = dbcursor.fetchall()
        for row in dato:
            if usuario == row[1] and password == row[3]:
                self.window2 = MainApp()
                self.close()
                self.window2.show()

            else:
                self.label.setText('Usuario o contraseña incorrectos')
"""


def seleccionar_imagen(carpeta='data_val'):
    imagen, extension = QFileDialog.getOpenFileName(None, "Seleccionar imagen", carpeta,
                                                    "Archivos de imagen (*.png *.jpeg)",
                                                    options=QFileDialog.Options())

    return imagen


class MainApp(QMainWindow, ui):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setupUi(self)
        self.UIcambios()
        self.botones()
        self.Dark_Gray_Tema()

        self.mostrarTodosPacientes()

    def UIcambios(self):
        self.tabWidget.tabBar().setVisible(False)

    def botones(self):
        self.pushButton_4.clicked.connect(self.prediccion_ventana_neumonia)
        self.pushButton_16.clicked.connect(self.prediccion_ventana_covid)
        self.btn_radiografias.setToolTip('Radiografia Neumonia')
        self.btn_radiografias.clicked.connect(self.rad_muestra_neumonia)
        self.btn_scans.setToolTip('CT Scan Covid')
        self.btn_scans.clicked.connect(self.rad_muestra_covid)

        self.pushButton.clicked.connect(self.abrirTabDeteccionRapida)
        self.pushButton_2.clicked.connect(self.abrirTabPacientes)
        self.pushButton_14.clicked.connect(self.abrirTabRadiografiasMuestra)
        self.pushButton_3.clicked.connect(self.abrirTabDoctores)

        self.pushButton_6.clicked.connect(self.agregarPaciente)
        self.pushButton_5.clicked.connect(self.confirmarAgregadoPaciente)
        self.pushButton_8.clicked.connect(self.buscarPaciente)
        self.pushButton_7.clicked.connect(self.editarPaciente)
        self.pushButton_9.clicked.connect(self.eliminarPaciente)

        self.pushButton_11.clicked.connect(self.agregarDoctor)
        self.pushButton_12.clicked.connect(self.iniciarSesion)
        self.pushButton_13.clicked.connect(self.editarDoctor)
        self.pushButton_17.clicked.connect(self.eliminarDoctor)

        self.pushButton_10.clicked.connect(self.editarRadiografia)
        self.pushButton_15.clicked.connect(self.ver_radiografia_paciente)

        self.pushButton_18.clicked.connect(self.exportarPacientes)



    #########################################
    ########### abrir pestañas ##############

    def abrirTabDeteccionRapida(self):
        self.tabWidget.setCurrentIndex(0)

    def abrirTabPacientes(self):
        self.tabWidget.setCurrentIndex(1)   

    def abrirTabRadiografiasMuestra(self):
        self.tabWidget.setCurrentIndex(2)

    def abrirTabDoctores(self):
        self.tabWidget.setCurrentIndex(3)



    #########################################
    ########### pacientes ##############

    def mostrarTodosPacientes(self):
        '''Muestra los datos de la tabla de pacientes en la intefarz'''
        dbcursor.execute('''
            SELECT nombre_paciente, edad, sexo, fecha_nacimiento, antecedentes FROM paciente ''')
        dato = dbcursor.fetchall()

        self.tableWidget.setRowCount(0)
        self.tableWidget.insertRow(0)

        for row, form in enumerate(dato):
            for columna, item in enumerate(form):
                self.tableWidget.setItem(row, columna, QTableWidgetItem(str(item)))
                columna += 1


            # obtener id del paciente de la tabla paciente
            dbcursor.execute('''
                SELECT id_paciente FROM paciente WHERE nombre_paciente=%s
            ''', [(form[0])])
            id_pac = dbcursor.fetchone()[0]

            # buscar id en la tabla de radiografias de neumonia y agregar la prediccion a la tabla de la interfaz
            stop = False
            try:
                dbcursor.execute('''
                    SELECT id_paciente, prediccion FROM radiografia_neumonia_paciente WHERE id_paciente=%s
                ''', [(id_pac)])
                datos_neumonia = dbcursor.fetchone()[1]
                self.tableWidget.setItem(row, columna, QTableWidgetItem(datos_neumonia))
            except TypeError: #'NoneType'
                stop = True

            # buscar id en la tabla de scans de covid y agregar la prediccion a la tabla de la interfaz
            if stop:
                try:
                    dbcursor.execute('''
                        SELECT id_paciente, prediccion FROM scan_covid_paciente WHERE id_paciente=%s
                    ''', [(id_pac)])
                    datos_covid = dbcursor.fetchone()[1]
                    self.tableWidget.setItem(row, columna, QTableWidgetItem(datos_covid))
                except TypeError: #'NoneType'
                    pass


            row_position = self.tableWidget.rowCount()
            self.tableWidget.insertRow(row_position)

        # self.db.close()


    def agregarRadiografia(self, radiografia):
        '''Convierte la imagen de la radiografia a binario'''
        with open(radiografia, 'rb') as File:
            binary_radiografia = File.read()

        return binary_radiografia


    def editarRadiografia(self):
        '''Edita la radiografia del paciente seleccionado'''
        try:
            # abrir ventana para seleccionar una radiografia
            self.radiografia = seleccionar_imagen()
            # hacer prediccion de la radiografia seleccionada
            self.pred = RedConvolucional()

            # predecir neumonia o covid dependiendo de la imagen seleccionada
            self.band = ''
            if 'chest_xray_val' in self.radiografia:
                predic = self.pred.prediccion_neumonia(self.radiografia)
                self.band = 'radiografia'
            elif 'ct_scans_val' in self.radiografia:
                predic = self.pred.prediccion_covid(self.radiografia)
                self.band = 'scan'

            # convertir imagen de la radiografia a binario para insertar en la tabla de base de datos
            binary_radiografia = self.agregarRadiografia(self.radiografia)
            # recuperar el nombre del paciente buscado
            buscar_nom_paciente = self.lineEdit_5.text()

            # actualizar la base de datos con los nuevos datos
            #-------------- EDITAR RADIOGRAFIA Y PREDICCION A OTRA TABLA --------------#
            dbcursor.execute('''
                SELECT id_paciente FROM paciente WHERE nombre_paciente=%s
            ''', [(buscar_nom_paciente)])
            id_pac = dbcursor.fetchone()[0]


            # elegir tabla para guardar radiografia
            if self.band == 'radiografia':
                try:
                    dbcursor.execute('''
                        UPDATE radiografia_neumonia_paciente SET radiografia_img=%s, prediccion=%s WHERE id_paciente=%s
                    ''', (binary_radiografia, predic, id_pac))

                    dbcursor.execute('''
                        SELECT id_paciente FROM radiografia_neumonia_paciente WHERE id_paciente=%s
                    ''', [(id_pac)])
                    id_pac_n = dbcursor.fetchone()[0]

                except TypeError: #'NoneType'
                    dbcursor.execute('''
                        INSERT INTO radiografia_neumonia_paciente (id_paciente, radiografia_img, prediccion) VALUES (%s, %s, %s)
                    ''', (id_pac, binary_radiografia, predic))

                    sql_tabla_covid = ''' DELETE FROM scan_covid_paciente WHERE id_paciente=%s '''
                    dbcursor.execute(sql_tabla_covid, [(id_pac)])


            # elegir tabla para guardar scan
            elif self.band == 'scan':
                try:
                    dbcursor.execute('''
                        UPDATE scan_covid_paciente SET ct_scan_img=%s, prediccion=%s WHERE id_paciente=%s
                    ''', (binary_radiografia, predic, id_pac))

                    dbcursor.execute('''
                        SELECT id_paciente FROM scan_covid_paciente WHERE id_paciente=%s
                    ''', [(id_pac)])
                    id_pac_c = dbcursor.fetchone()[0]

                except TypeError: #'NoneType'
                    dbcursor.execute('''
                        INSERT INTO scan_covid_paciente (id_paciente, ct_scan_img, prediccion) VALUES (%s, %s, %s)
                    ''', (id_pac, binary_radiografia, predic))

                    sql_tabla_neumonia = ''' DELETE FROM radiografia_neumonia_paciente WHERE id_paciente=%s '''
                    dbcursor.execute(sql_tabla_neumonia, [(id_pac)])


            # confirmar el cambio en la base de datos
            bd.commit()
            self.statusBar().showMessage('Radiografia editada')

            self.mostrarTodosPacientes()
        
        except FileNotFoundError:
            self.statusBar().showMessage('')


    def agregarPaciente(self):
        '''Agrega pacientes a la base de datos'''
        try:
            # campos de donde obtenemos los datos del paciente
            nombre_paciente = self.lineEdit.text()
            edad_paciente = self.lineEdit_2.text()
            sexo_paciente = self.comboBox.currentText()
            temp_fecha = self.dateEdit.date()
            fecha_nacimiento_paciente = temp_fecha.toPyDate()
            situacion_laboral_paciente = self.comboBox_3.currentText()
            estado_civil_paciente = self.comboBox_2.currentText()
            antecedentes_paciente = self.textEdit.toPlainText()

            # abrir ventana para seleccionar una radiografia
            self.radiografia = seleccionar_imagen()
            # hacer prediccion de la radiografia seleccionada
            self.pred = RedConvolucional()

            # predecir neumonia o covid dependiendo de la imagen seleccionada
            self.band = ''
            if 'chest_xray_val' in self.radiografia:
                predic = self.pred.prediccion_neumonia(self.radiografia)
                self.band = 'radiografia'
            elif 'ct_scans_val' in self.radiografia:
                predic = self.pred.prediccion_covid(self.radiografia)
                self.band = 'scan'

            # convertir imagen de la radiografia a binario para insertar en la tabla de base de datos
            radiografia_paciente = self.agregarRadiografia(self.radiografia)

            # insertar los datos ingresados en la base de datos
            dbcursor.execute('''
                INSERT INTO paciente (nombre_paciente, edad, sexo, fecha_nacimiento, estado_civil, situacion_laboral, antecedentes)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (nombre_paciente, edad_paciente, sexo_paciente, fecha_nacimiento_paciente, estado_civil_paciente, situacion_laboral_paciente, antecedentes_paciente))


            #-------------- AGREGAR RADIOGRAFIA Y PREDICCION A OTRA TABLA --------------#
            # obtener id del paciente
            dbcursor.execute('''
                SELECT id_paciente FROM paciente WHERE nombre_paciente=%s
            ''', [(nombre_paciente)])
            id_pac = dbcursor.fetchone()[0]

            # insertar la radiografia y su prediccion en la base de datos, en la tabla de radiografias o scans
            if self.band == 'radiografia':
                dbcursor.execute('''
                    INSERT INTO radiografia_neumonia_paciente (id_paciente, radiografia_img, prediccion) VALUES (%s, %s, %s)
                ''', (id_pac, radiografia_paciente, predic))
            elif self.band == 'scan':
                dbcursor.execute('''
                    INSERT INTO scan_covid_paciente (id_paciente, ct_scan_img, prediccion) VALUES (%s, %s, %s)
                ''', (id_pac, radiografia_paciente, predic))


            # confirmar el cambio en la base de datos
            bd.commit()
            self.statusBar().showMessage('Radiografia seleccionada')

            self.radiografia_ver = VerRadiografia()
            self.radiografia_ver.ver_radiografia(nombre_paciente)
            self.radiografia_ver.exec()

            self.mostrarTodosPacientes()

            # self.confirmarAgregadoPaciente()

        except FileNotFoundError:
            self.statusBar().showMessage('')


    def confirmarAgregadoPaciente(self):
        '''limpia los campos despues de agregar la informacion de un paciente'''
        # boton 'guardar'
        self.statusBar().showMessage('Paciente Agregado')

        # limpiar los campos despues de agregar la informacion de un paciente
        self.lineEdit.setText('')
        self.lineEdit_2.setText('')
        self.comboBox.setCurrentIndex(0)
        self.dateEdit.setDate(datetime.date(1920, 1, 1))
        self.comboBox_3.setCurrentIndex(0)
        self.comboBox_2.setCurrentIndex(0)
        self.textEdit.setPlainText('')


    def buscarPaciente(self):
        '''Busca un paciente a traves del nombre'''
        # recuperar el nombre del paciente buscado
        nom_paciente = self.lineEdit_5.text()

        try:
            # seleccionar todos datos de la tabla paciente
            sql = ''' SELECT * FROM paciente WHERE nombre_paciente = %s '''
            dbcursor.execute(sql, [(nom_paciente)])

            # guardar los datos de la tabla
            dato = dbcursor.fetchone()
            # labels ocultos con mensaje 'no se encuentra paciente' y 'no se encuentra radiografia'
            self.label_38.setText(' ')
            self.label_39.setText(' ')

            # mostrar los datos de la tabla en la interfaz
            self.lineEdit_3.setText(dato[1])
            self.lineEdit_4.setText(str(dato[2]))
            self.comboBox_6.setCurrentText(dato[3])
            self.dateEdit_2.setDate(dato[4])
            self.comboBox_4.setCurrentText(dato[5])
            self.comboBox_5.setCurrentText(dato[6])
            self.textEdit_2.setPlainText(dato[7])

        except TypeError:
            self.label_38.setText('No se encuentra ese paciente')


    def editarPaciente(self):
        '''Edita los datos de un paciente'''
        # campos de donde obtenemos los datos del paciente
        nombre_paciente = self.lineEdit_3.text()
        edad_paciente = self.lineEdit_4.text()
        sexo_paciente = self.comboBox_6.currentText()
        temp_fecha = self.dateEdit_2.date()
        fecha_nacimiento_paciente = temp_fecha.toPyDate()
        estado_civil_paciente = self.comboBox_4.currentText()
        situacion_laboral_paciente = self.comboBox_5.currentText()
        antecedentes_paciente = self.textEdit_2.toPlainText()

        # nombre del paciente buscado
        buscar_nom_paciente = self.lineEdit_5.text()

        # actualizar la base de datos con los nuevos datos
        dbcursor.execute('''
            UPDATE paciente SET nombre_paciente=%s, edad=%s, sexo=%s, fecha_nacimiento=%s, estado_civil=%s, situacion_laboral=%s, antecedentes=%s WHERE nombre_paciente=%s
        ''', (nombre_paciente, edad_paciente, sexo_paciente, fecha_nacimiento_paciente, estado_civil_paciente, situacion_laboral_paciente, antecedentes_paciente, buscar_nom_paciente))

        # confirmar el cambio en la base de datos
        bd.commit()
        self.statusBar().showMessage('Datos de Paciente Editados')

        self.mostrarTodosPacientes()

    
    def eliminarPaciente(self):
        '''Elimina un paciente'''
        # nombre del paciente buscado
        nom_paciente = self.lineEdit_5.text()

        # mensaje de advertencia
        warning = QMessageBox.warning(self, 'Eliminar Paciente', "¿Esta seguro que quiere eliminar este paciente?", QMessageBox.Yes | QMessageBox.No)
        if warning == QMessageBox.Yes:

            dbcursor.execute('''
                SELECT id_paciente FROM paciente WHERE nombre_paciente=%s
            ''', [(nom_paciente)])
            id_pac = dbcursor.fetchone()[0]

            # eliminar registro de la tabla radiografia_neumonia_paciente
            sql_tabla_neumonia = ''' DELETE FROM radiografia_neumonia_paciente WHERE id_paciente=%s '''
            dbcursor.execute(sql_tabla_neumonia, [(id_pac)])

            # eliminar registro de la tabla scan_covid_paciente
            sql_tabla_covid = ''' DELETE FROM scan_covid_paciente WHERE id_paciente=%s '''
            dbcursor.execute(sql_tabla_covid, [(id_pac)])

            # eliminar registro de la tabla paciente
            sql_tabla_paciente = ''' DELETE FROM paciente WHERE nombre_paciente=%s '''
            dbcursor.execute(sql_tabla_paciente, [(nom_paciente)])

            # confirmar el cambio en la base de datos
            bd.commit()
            self.statusBar().showMessage('Paciente Eliminado')

        self.mostrarTodosPacientes()
    


    #########################################
    ########### doctores ##############
    
    def agregarDoctor(self):
        '''Agrega un nuevo usuario'''

        # obtener la informacion ingresada desde la interfaz
        usuario = self.lineEdit_6.text()
        email = self.lineEdit_7.text()
        password = self.lineEdit_8.text()
        password2 = self.lineEdit_9.text()

        if password == password2:
            dbcursor.execute('''
                INSERT INTO doctor(nombre_doctor, email_doctor, password_doctor) 
                VALUES (%s, %s, %s)
            ''', (usuario, email, password))

            bd.commit()
            self.statusBar().showMessage('Nuevo Usuario Agregado')

        else:
            self.label_37.setText('Ingrese una contraseña valida')

    
    def iniciarSesion(self):
        '''Inicar sesion para usar la aplicacion'''

        usuario = self.lineEdit_10.text()
        password = self.lineEdit_11.text()

        sql = ''' SELECT * FROM doctor '''
        dbcursor.execute(sql)
        data = dbcursor.fetchall()

        for row in data:
            if usuario == row[1] and password == row[3]:
                self.statusBar().showMessage('Nombre y contraseña validos')
                self.groupBox_3.setEnabled(True)

                self.lineEdit_13.setText(row[1])
                self.lineEdit_12.setText(row[2])
                self.lineEdit_15.setText(row[3])

    
    def editarDoctor(self):
        '''Edita los datos de un usuario'''

        usuario = self.lineEdit_13.text()
        email = self.lineEdit_12.text()
        password = self.lineEdit_15.text()
        password2 = self.lineEdit_14.text()

        usuario_original = self.lineEdit_10.text()

        if password == password2:
            dbcursor.execute('''
                UPDATE doctor SET nombre_doctor=%s, email_doctor=%s, password_doctor=%s WHERE nombre_doctor=%s
            ''', (usuario, email, password, usuario_original))

            bd.commit()
            self.statusBar().showMessage('Informacion Editada Correctamente')

        else:
            print('Contraseña incorrecta')
            self.statusBar().showMessage('Contraseña incorrecta')


    def eliminarDoctor(self):
        '''Elimina a un usuario'''

        # nombre del usuario buscado
        usuario = self.lineEdit_13.text()
        # email = self.lineEdit_12.text()
        password = self.lineEdit_15.text()
        password2 = self.lineEdit_14.text()

        sql = ''' SELECT password_doctor FROM doctor WHERE nombre_doctor=%s '''
        dbcursor.execute(sql, [(usuario)])
        password_doctor = dbcursor.fetchone()[0]

        if password == password_doctor and password == password2:
            # mensaje de advertencia
            warning = QMessageBox.warning(self, 'Eliminar Usuario', "¿Esta seguro que quiere eliminar este usuario?", QMessageBox.Yes | QMessageBox.No)
            if warning == QMessageBox.Yes:

                # eliminar registro de la tabla paciente
                sql = ''' DELETE FROM doctor WHERE nombre_doctor=%s '''
                dbcursor.execute(sql, [(usuario)])

                # confirmar el cambio en la base de datos
                bd.commit()
                self.statusBar().showMessage('Usuario Eliminado')

        else:
            print('Contraseña incorrecta')
            self.statusBar().showMessage('Contraseña incorrecta')


    ###################################################################
    ########### exportar pacientes a un archivo excel ##############
    def exportarPacientes(self):
        '''Crea un archivo de excel con los datos de los pacientes'''

        dbcursor.execute('''SELECT nombre_paciente, edad, sexo, fecha_nacimiento, estado_civil, situacion_laboral, antecedentes FROM paciente''')
        # id_pac = dbcursor.fetchone()[0]
        dato = dbcursor.fetchall()

        archivo = Workbook('pacientes.xlsx')
        sheet1  = archivo.add_worksheet()

        sheet1.write(0,0,'nombre')
        sheet1.write(0,1,'edad')
        sheet1.write(0,2,'sexo')
        sheet1.write(0,3,'fecha nacimiento')
        sheet1.write(0,4,'estado civil')
        sheet1.write(0,5,'situacion laboral')
        sheet1.write(0,6,'antecedentes')
        sheet1.write(0,7,'prediccion')

        numero_fila = 1
        for fila in dato:
            numero_columna = 0
            for item in fila :
                sheet1.write(numero_fila, numero_columna, str(item))
                numero_columna += 1


            # obtener id del paciente de la tabla paciente
            dbcursor.execute('''
                SELECT id_paciente FROM paciente WHERE nombre_paciente=%s
            ''', [(fila[0])])
            id_pac = dbcursor.fetchone()[0]

            # buscar id en la tabla de radiografias de neumonia y agregar la prediccion a la tabla de la interfaz
            stop = False
            try:
                dbcursor.execute('''
                    SELECT id_paciente, prediccion FROM radiografia_neumonia_paciente WHERE id_paciente=%s
                ''', [(id_pac)])
                # datos = dbcursor.fetchall()
                datos_neumonia = dbcursor.fetchone()[1]
                sheet1.write(numero_fila, numero_columna, str(datos_neumonia))

            except TypeError: #'NoneType'
                stop = True

            # buscar id en la tabla de scans de covid y agregar la prediccion a la tabla de la interfaz
            if stop:
                try:
                    dbcursor.execute('''
                        SELECT id_paciente, prediccion FROM scan_covid_paciente WHERE id_paciente=%s
                    ''', [(id_pac)])
                    datos_covid = dbcursor.fetchone()[1]
                    sheet1.write(numero_fila, numero_columna, str(datos_covid))

                except TypeError: #'NoneType'
                    pass
            
            numero_fila += 1

        archivo.close()
        self.statusBar().showMessage('Reporte de pacientes Creado Exitosamente')



    #########################################
    ########### ventanas de radiografias ##############

    ###### Radiografia de muestra Neumonia ######
    def rad_muestra_neumonia(self):
        '''Mostrar una radiografia aleatoria de la tabla de neumonia'''
        self.ventana_rad_muestra = RadiografiaMuestra()
        self.ventana_rad_muestra.ventana_radiografia_muestra('radiografia_neumonia_paciente', 'img_salida/img_no.jpg')
        self.ventana_rad_muestra.exec()

    ###### Scans de muestra Covid ######
    def rad_muestra_covid(self):
        '''Mostrar una ct scan aleatoria de la tabla de covid'''
        self.ventana_rad_muestra = RadiografiaMuestra()
        self.ventana_rad_muestra.ventana_radiografia_muestra('scan_covid_paciente', 'img_salida/img_si.jpg')
        self.ventana_rad_muestra.exec()

    ###### Prediccion rapida Neumonia ######
    def prediccion_ventana_neumonia(self):
        '''Mostrar la imagen y la prediccion rapida de una radiografia de neumonia'''
        self.ventana_prediccion = RedConvolucional()
        self.ventana_prediccion.predicciones_rapidas('data_val/chest_xray_val')
        self.ventana_prediccion.exec()

    ###### Prediccion rapida Covid ######
    def prediccion_ventana_covid(self):
        '''Mostrar la imagen y la prediccion rapida de una ct scan de covid'''
        self.ventana_prediccion = RedConvolucional()
        self.ventana_prediccion.predicciones_rapidas('data_val/ct_scans_val')
        self.ventana_prediccion.exec()
    
    ###### Ver radiografia de un paciente (al editar datos del paciente) ######
    def ver_radiografia_paciente(self):
        '''Ver la radiografia o scan de un paciente en la seccion de editar paciente'''

        # nombre del paciento buscado
        nombre = self.lineEdit_5.text()
        try:
            self.label_39.setText(' ')
            self.radiografia = VerRadiografia()
            self.radiografia.ver_radiografia(nombre)
            self.radiografia.exec()

        except TypeError:
            self.label_39.setText('No se encuentra radiografia')



    #########################################
    ########### Temas UI ##############

    def Dark_Blue_Tema(self):
        style = open('temas/darkblue.css', 'r')
        style = style.read()
        self.setStyleSheet(style)

    def Dark_Gray_Tema(self):
        style = open('temas/darkgray.css', 'r')
        style = style.read()
        self.setStyleSheet(style)

    def Dark_Orange_Tema(self):
        style = open('temas/darkorange.css', 'r')
        style = style.read()
        self.setStyleSheet(style)

    def QDark_Tema(self):
        style = open('temas/qdark.css', 'r')
        style = style.read()
        self.setStyleSheet(style)





###### Desplegar ventana para ver la imagen o prediccion ######
class VentanaImagen(QDialog, radiografia):
    '''Crea la ventana para mostrar las radiografias y las predicciones'''

    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)

    def mostrar_ventana(self, imagen, prediccion=None):
        # escalar la imagen
        imagen = QPixmap(imagen).scaled(600, 700, Qt.KeepAspectRatio,
                                                Qt.SmoothTransformation)

        # mostrar la imagen en una ventada
        self.label = QLabel(self.label_imagen)
        self.rad = QPixmap(imagen)
        self.resize(self.rad.width(),self.rad.height()+80) # ajustar la ventana al tamaño de la imagen
        self.label.setPixmap(self.rad)
        self.label_prediccion.setText(prediccion)


###### Ver radiografia del paciente en la seccion de edicion de datos ######
class VerRadiografia(VentanaImagen):
    '''Selecciona las radiografias y las predicciones a mostrar en las diferentes secciones'''

    def ver_radiografia(self, nombre):
        # obtener id del paciente de la tabla paciente
        sql = "SELECT id_paciente FROM paciente WHERE nombre_paciente = %s"
        dbcursor.execute(sql, [(nombre)])
        id_pac = dbcursor.fetchone()[0]

        # buscar id en la tabla de radiografias de neumonia y agregar la prediccion a la tabla de la interfaz
        band = False
        try:
            sql_neumonia = "SELECT id_paciente, radiografia_img, prediccion FROM radiografia_neumonia_paciente WHERE id_paciente=%s"
            dbcursor.execute(sql_neumonia, [(id_pac)])
            datos_neumonia = dbcursor.fetchone()
            # guardar la radiografia y la prediccion en variables
            nom_img = datos_neumonia[1]
            pred = datos_neumonia[2]
            ruta_guardar_img = 'img_salida/img_rad.jpg'
        except TypeError: #'NoneType'
            band = True

        # buscar id en la tabla de scans de covid y agregar la prediccion a la tabla de la interfaz
        if band:
            try:
                sql_covid = "SELECT id_paciente, ct_scan_img, prediccion FROM scan_covid_paciente WHERE id_paciente=%s"
                dbcursor.execute(sql_covid, [(id_pac)])
                datos_covid = dbcursor.fetchone()
                # guardar la radiografia y la prediccion en variables
                nom_img = datos_covid[1]
                pred = datos_covid[2]
                ruta_guardar_img = 'img_salida/img_rad.jpg'
            except TypeError: #'NoneType'
                pass

        # guardar la radiografia en un archivo .jpg
        with open(ruta_guardar_img, 'wb') as archivo:
            archivo.write(nom_img)
            archivo.close()

        self.mostrar_ventana(ruta_guardar_img, pred)


###### Ventana Radiografia de muestra Normal y neumonia ######
class RadiografiaMuestra(VentanaImagen):
    '''Selecciona las radiografias y predicciones a mostrar en la seccion de "radiografias de muestra"'''

    def ventana_radiografia_muestra(self, tabla, ruta_guardar_img):
        # seleccionar los ids y las predicciones de las tablas
        sql_filas = "SELECT id_paciente, prediccion FROM {0}"
        dbcursor.execute(sql_filas.format(tabla))
        datos_tabla = dbcursor.fetchall()

        # diccionario con los ids y las predicciones
        filas_lista = {}
        for i in datos_tabla:
            filas_lista[i[0]] = i[1]

        # elegir un id aleatoreo
        fila = random.choice(list(filas_lista.keys()))

        # guardar imagen para mostrar
        sql = "SELECT * FROM {0} WHERE id_paciente = '{1}'"
        dbcursor.execute(sql.format(tabla, str(fila)))
        id_img = dbcursor.fetchone()[1]
        ruta_guardar_img = ruta_guardar_img.format(str(fila))

        with open(ruta_guardar_img, 'wb') as archivo:
            archivo.write(id_img)
            archivo.close()

        self.mostrar_ventana(ruta_guardar_img, filas_lista[fila])




###### RED NEURONAL Y PREDICCION ######
class RedConvolucional(VentanaImagen):
    '''Procesamiento de las imagenes y predicciones con la red neuronal convolucional'''

    def pred_porcentajes(self, pred=None, img=None, enf=None):
        '''Mostrar los porcentajes y la imagen de la prediccion'''

        self.list_index = [0,1]
        x = pred
        for i in range(2):
            for j in range(2):
                if x[0][self.list_index[i]] > x[0][self.list_index[j]]:
                    temp = self.list_index[i]
                    self.list_index[i] = self.list_index[j]
                    self.list_index[j] = temp

        i=0
        self.porcentaje = round(pred[0][self.list_index[i]] * 100, 2)
        self.clasificaciones = [enf + ': NO\n' + str(self.porcentaje) + '%', \
                           enf + ': SI\n' + str(self.porcentaje) + '%']
        for i in range(2):
            print(self.clasificaciones[self.list_index[i]], ':', round(pred[0][self.list_index[i]] * 100, 2), '%')
        
        self.pred1 = round(pred[0][self.list_index[0]] * 100, 2)
        self.pred2 = round(pred[0][self.list_index[1]] * 100, 2)

        if self.pred1 > self.pred2:
            pred_ventana = self.clasificaciones[self.list_index[0]]
            self.mostrar_ventana(img, pred_ventana)
            return pred_ventana
        else:
            pred_ventana = self.clasificaciones[self.list_index[1]]
            self.mostrar_ventana(img, pred_ventana)
            return pred_ventana



    def prediccion_neumonia(self, radiografia=None):
        '''Prediccion de Radiografias de Neumonia'''

        # cargar la imagen seleccionada
        # imagen = cv2.imread(self.imagen)
        imagen = skimage.io.imread(radiografia)
        
        # reescalar la imagen a un tamaño de 150 x 150
        imagen = skimage.transform.resize(imagen, (150,150,3), mode='constant', anti_aliasing=True)
        # convertir la imagen a un array
        self.np_imagen = np.array(imagen)

        # imagen en gris (blanco y negro)
        self.np_imagen = rgb2gray(self.np_imagen)
        # cambiar la forma para la prediccion (agregar una dimension)
        self.np_imagen = self.np_imagen.reshape(1,150,150,1)

        # prediccion
        self.predicciones = rnc_model.predict(self.np_imagen)
        # array con el resultado de la prediccion
        # self.prediccion_imagen = np.argmax(self.resultado[0])

        return self.pred_porcentajes(self.predicciones, radiografia, 'Neumonia')

  

    def prediccion_covid(self, ct_scan=None):
        '''Prediccion de Scans de Covid'''
        
        # cargar la imagen seleccionada
        # image = cv2.imread(ct_scan)
        imagen = skimage.io.imread(ct_scan)
        # reescalar la imagen a un tamaño de 150 x 150
        self.imagen_reescalada = skimage.transform.resize(imagen, (64,64,3))
        # prediccion
        self.predicciones = rnc_model_covid.predict(np.array( [self.imagen_reescalada] ))

        return self.pred_porcentajes(self.predicciones, ct_scan, 'Covid')



    def predicciones_rapidas(self, carpeta='data_val'):
        '''Prediccion rapida de radiografias de Neumonia y scans de Covid'''

        self.imagen = seleccionar_imagen(carpeta)

        if 'chest_xray_val' in self.imagen:
            self.prediccion_neumonia(self.imagen)
        elif 'ct_scans_val' in self.imagen:
            self.prediccion_covid(self.imagen)

    





def main():
    app = QApplication(sys.argv)
    # window = Login()
    window = MainApp()
    window.show()
    app.exec_()


if __name__ == '__main__':
    main()





