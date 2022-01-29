from email import message
import os
import json
from pickle import FALSE
from turtle import st
import requests
from zipfile import ZipFile
import time


from qgis.PyQt import uic
from qgis.PyQt import QtWidgets #QtGui
from qgis.core import QgsProject, Qgis
from qgis.PyQt.QtWidgets import QFileDialog

from .report import ReportDialog
from .worker import Worker

from PyQt5.QtCore import QThread, pyqtSignal, QSize


#from .login import LoginDialog

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'UploadPalapa_main.ui'))

class UploadDialog(QtWidgets.QDialog, FORM_CLASS):

    UserLogout = pyqtSignal()
  
    def __init__(self, parent=None):
        """Constructor."""
        super(UploadDialog, self).__init__(parent)
        self.setupUi(self)
        #self.login = LoginDialog()
        self.upload.setEnabled(True)
        self.upload.clicked.connect(self.checking)
        self.browse_metadata.clicked.connect(self.start_browse_metadata)
        self.browse_style.clicked.connect(self.start_browse_style)
        self.url = None
        self.simpulJaringan=None
        self.grup = None
        self.user=None
        self.pathMeta = None
        self.MetaRun = False
        self.pathSLD = None
        self.UserParams = None
        self.LayerParams = None
        self.filesSld = None
        self.SLDqgis = False
        self.lineEdit_metadata.setReadOnly(True)
        self.lineEdit_style.setReadOnly(True)
        self.radioButton_StyleBrowse.toggled.connect(self.browse_style.setEnabled)
        self.radioButton_StyleBrowse.toggled.connect(self.lineEdit_style.setEnabled)
        self.pushButton_clearStyle.clicked.connect(self.clearStyle)
        self.pushButton_clearMetadata.clicked.connect(self.clearMetadata)
        #self.pushButton_logout.clicked.connect(self.logout)
        self.label_logout.mousePressEvent = self.logout

        # self.thread = None
        # self.bar = QgsMessageBar()
        # self.bar.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        # self.layout().addWidget(self.bar)

        # self.progress_gif = QtGui.QMovie(
        #     ":/plugins/Plugin-upload-palapa/img/loader.svg")
        # self.progress_gif.setScaledSize(QSize(32, 32))

        self.ReportDlg = ReportDialog()


    def logout(self, event):
        self.UserLogout.emit()

    def UserParam(self, signalpayload):
        print('signal nangkep',signalpayload)
        self.grup = signalpayload['grup']
        self.user = signalpayload['user']
        self.url = signalpayload['url']
        self.simpulJaringan = signalpayload['kodesimpul']
        self.label_userdesc.setText(f"Anda masuk sebagai {self.user} pada {self.url}")
        print(signalpayload)
        self.UserParams = signalpayload
    
    #Upload Tab2
    # def startworker(self):
    #     self.thread = ThreadClass(parent = None)
    #     self.thread.start()
    #     self.thread.any_signal.connect(self.uploadFile)

    def checking(self):
        if((self.radioButton_StyleBrowse.isChecked() and self.pathSLD == '') or (self.radioButton_StyleBrowse.isChecked() and self.pathSLD == None)):
            self.report(self.label_statusbase, 'caution', 'Masukkan SLD atau gunakan SLD bawaan')
            print('masukkan SLD atau gunakan sld bawaan')
        else:
            layerPath = self.exportLayer()
            # define layer parameter
            self.LayerParams = layerPath
            if self.checkFileExist(layerPath['shp']) and self.checkFileExist(layerPath['dbf']) and self.checkFileExist(layerPath['shx']) and self.checkFileExist(layerPath['prj']) :
                print("file Lengkap")
                if(self.radioButton_StyleQgis.isChecked()):      
                    self.SLDqgis = True              
                    sldPath = self.exportSld()
                elif(self.radioButton_StyleBrowse.isChecked() and (self.pathSLD != '' or self.pathSLD != None)):    
                    sldPath = self.pathSLD
                # define SLD parameter
                self.filesSld = {'file': open(sldPath,'rb')}
                print(self.filesSld)
                if (self.pathMeta is not None and self.pathMeta != ''):
                    print('metajalan',self.pathMeta)         
                    self.MetaRun = True
                self.runUpload()
                
            else :
                print("file Tidak Lengkap")
            
                
    
    def runUpload(self):
        self.thread = QThread()
        self.worker = Worker(self.UserParams, self.LayerParams, self.filesSld, self.SLDqgis, self.pathMeta, self.MetaRun)
        self.worker.moveToThread(self.thread) # move Worker-Class to a thread
        # Connect signals and slots:
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.worker.status.connect(self.reportStatus)
        self.worker.progress.connect(self.reportProgress)

        self.thread.start() # finally start the thread
        self.ReportDlg.show()
        self.ReportDlg.progressBar.setValue(0)
        self.thread.finished.connect(self.reportFinish)
        self.upload.setEnabled(False) # disable the start-upload button while thread is running
        self.thread.finished.connect(lambda: self.upload.setEnabled(True)) # enable the start-thread button when thread has been finished

    def reportProgress(self, val):
        self.report(self.label_statusbase, 'caution', f'Sedang diproses . . . ({val}/4))')
        self.ReportDlg.progressBar.setValue(val/4*100)
    
    def reportStatus(self, status):
        label = status["label"]
        result = status["result"]
        message = status["msg"]
        if label == 'SLD':
            self.ReportDlg.report(self.ReportDlg.label_statusSLD, result, message)
        elif label == 'layer':
            self.ReportDlg.report(self.ReportDlg.label_statusLayer, result, message)
        elif label == 'publish':
            self.ReportDlg.report(self.ReportDlg.label_statusPublish, result, message)
        elif label == 'metadata':
            self.ReportDlg.report(self.ReportDlg.label_statusMetadata, result, message)
        elif label == 'general':
            self.ReportDlg.report(self.ReportDlg.label_statusgeneral, result, message)
            self.report(self.label_statusbase, result, message)

    def reportFinish(self):
        self.report(self.label_statusbase, True, 'Proses Selesai')
        

    # def uploadFile(self):
    #     self.reportReset()
    #     #self.ReportDlg.show()
    #     #self.bar.pushMessage("Proses", "Unggah layer sedang diproses", level=Qgis.Info, duration=0)
    #     #self.report(self.label_statusbase, 'caution', 'Sedang diproses . . .')
    #     if((self.radioButton_StyleBrowse.isChecked() and self.pathSLD == '') or (self.radioButton_StyleBrowse.isChecked() and self.pathSLD == None)):
    #         # self.report(self.label_statusSLD, 'caution', 'Masukkan SLD atau gunakan SLD bawaan')
    #         print('masukkan SLD atau gunakan sld bawaan')
    #     else:
    #         layerPath = self.exportLayer()
    #         if self.checkFileExist(layerPath['shp']) and self.checkFileExist(layerPath['dbf']) and self.checkFileExist(layerPath['shx']) and self.checkFileExist(layerPath['prj']) :
    #             print("file Lengkap")
    #             if(self.radioButton_StyleQgis.isChecked()):
    #                 sldPath = self.exportSld()
    #             elif(self.radioButton_StyleBrowse.isChecked() and (self.pathSLD != '' or self.pathSLD != None)):    
    #                 sldPath = self.pathSLD
    #             filesSld = {'file': open(sldPath,'rb')}

    #             #upload SLD
    #             params = {"USER":self.user,"GRUP":self.grup,"KODESIMPUL":self.simpulJaringan}
    #             urlSld = self.url+"/api/styles/add"
    #             responseAPISld = requests.post(urlSld,files=filesSld,params=params)
    #             print(responseAPISld.text)
    #             print(filesSld)
    #             responseAPISldJSON = json.loads(responseAPISld.text)
    #             if(responseAPISldJSON['MSG'] == 'Upload Success!'):
    #                 self.bar.pushMessage("SLD Berhasil diunggah!", responseAPISldJSON['RTN'], level=Qgis.Success, duration=0)
    #             #    self.report(self.label_statusSLD, True, 'SLD Berhasil diunggah! ('+ responseAPISldJSON['RTN']+')')
    #             else:
    #                 self.bar.pushMessage("SLD Gagal diunggah!", f"{responseAPISldJSON['MSG']} ({responseAPISldJSON['RTN']})", level=Qgis.Critical, duration=0)
    #             #    self.report(self.label_statusSLD, False, 'SLD Gagal diunggah! : '+responseAPISldJSON['MSG'] +' ('+ responseAPISldJSON['RTN']+')')
                
    #             zipShp = ZipFile(f"{layerPath['shp'].split('.')[0]}"+'.zip', 'w')

    #             # Add multiple files to the zip
    #             print(layerPath['shp'].split('.')[0].split('/')[-1])
    #             zipShp.write(f"{layerPath['shp']}",os.path.basename(layerPath['shp']).replace(" ","_"))
    #             zipShp.write(f"{layerPath['dbf']}",os.path.basename(layerPath['dbf']).replace(" ","_"))
    #             zipShp.write(f"{layerPath['shx']}",os.path.basename(layerPath['shx']).replace(" ","_"))
    #             zipShp.write(f"{layerPath['prj']}",os.path.basename(layerPath['prj']).replace(" ","_"))
    #             # close the Zip File
    #             zipShp.close()
                
    #             files = {'file': open(f"{layerPath['shp'].split('.')[0]}"+'.zip','rb')}
    #             print(files)
                
    #             urlUpload = self.url+"/api/upload"
    #             responseAPIZip = requests.post(urlUpload,files=files,params=params)
    #             dataPublish = json.loads(responseAPIZip.text)
    #             print(dataPublish,"publish")
    #             self.publish(dataPublish['SEPSG'],dataPublish['LID'],dataPublish['TIPE'],dataPublish['ID'])
    #             self.linkStyleShp(dataPublish['LID'],dataPublish['ID'])
    #             # if(dataPublish['RTN'] == self.select_layer.currentText()+'.zip'):
    #             #     self.report(self.label_statusLayer, True, 'Layer Berhasil diunggah! : '+dataPublish['MSG']+' ('+dataPublish['RTN']+')')
    #             # else:
    #             #     self.report(self.label_statusLayer, False, 'Layer Gagal diunggah! : '+dataPublish['MSG'])            
                
    #             #metadata
    #             if (self.pathMeta is not None and self.pathMeta != ''):
    #                 print('upload meta jalan',self.pathMeta)         
    #                 self.uploadMetadata(dataPublish['LID'])
                
    #             if (self.radioButton_StyleQgis.isChecked()):
    #                 filesSld['file'].close()
    #                 os.remove(sldPath)
    #             files['file'].close() 
    #             os.remove(layerPath['shp'].split('.')[0]+'.zip')

    #         else :
    #             print("file Tidak Lengkap")


    def clearStyle(self):
        self.lineEdit_style.setText('')
        self.filename1 = ''
        self.pathSLD = None

    def clearMetadata(self):
        self.lineEdit_metadata.setText('')
        self.filename1 = ''
        self.pathMeta = None

    # def publish(self,kodeEpsg,Lid,Tipe,id):
    #     url = self.url + "/api/publish"
    #     dataPublish = {"pubdata":{"LID": Lid, "TIPE": Tipe,"ID":id,"ABS":"","SEPSG":kodeEpsg,"USER":self.user,"GRUP":self.grup}}
    #     dataPublish = json.dumps(dataPublish)
    #     respond = requests.post(url,data=f"dataPublish={dataPublish}")
    #     print(respond.text)
    #     respondJSON = json.loads(respond.text)
    #     # if(respondJSON['RTN']):
    #     #     self.report(self.label_statusPublish, True, 'Layer Berhasil dipublikasikan! : '+respondJSON['MSG'])
    #     # else:
    #     #     self.report(self.label_statusPublish, False, 'Layer Gagal dipublikasikan! : '+respondJSON['MSG'])
      
    def exportLayer(self):
        layerName = self.select_layer.currentText()
        layer = QgsProject().instance().mapLayersByName(layerName)[0]
        source = layer.source()
  
        source = source.split("|")
        EPSGLayer = layer.crs().authid()
  
        tipe = source[0].split(".")[-1]
        if (tipe=="shp"):
            sourceFile = self.replacePath(source[0],".shp")
        elif (tipe=="dbf"):
            sourceFile = self.replacePath(source[0],".dbf")
        elif (tipe=="shx"):
            sourceFile = self.replacePath(source[0],".shx")
        return sourceFile

    # def linkStyleShp(self,Lid,style):
    #     url = self.url + "/api/layers/modify"
    #     dataPublish = {"pubdata":{"id": Lid,"aktif":False, "tipe": "VECTOR","abstract":"","nativename":f"{self.grup}:{Lid}","style":style,"title":style}}
    #     dataPublish = json.dumps(dataPublish)
    #     respond = requests.post(url,data=f"dataPublish={dataPublish}")
    #     print(respond.text)        
   
    def replacePath(self,source,tipeFile):
        print(tipeFile)
        shp = source.replace(tipeFile, ".shp")
        shp = shp.replace("\\", "/")
        prj = source.replace(tipeFile, ".prj")
        prj = prj.replace("\\", "/")
        dbf = source.replace(tipeFile, ".dbf")
        dbf = dbf.replace("\\", "/")
        shx = source.replace(tipeFile, ".shx")
        shx = shx.replace("\\", "/")
        sourceFile = json.loads('{"shp":"%s","prj":"%s","dbf":"%s","shx":"%s"}'%(shp,prj,dbf,shx))
        print(sourceFile)
        return sourceFile
    
    def checkFileExist(self,filePath):
        fileExist = True
        if os.path.isfile(filePath):
            print ("File exist")
            fileExist = True
        else:
            print ("File not exist")
            fileExist = False
        return fileExist

    def exportSld(self):
        layerName = self.select_layer.currentText()
        layer = QgsProject().instance().mapLayersByName(layerName)[0]
        source = layer.source()
        source = source.split("|")[0]
        tipe = source.split(".")[-1]
        if(tipe=="shp"):
            sldPath = source.replace(".shp", ".sld")
        elif(tipe=="shx"):
            sldPath = source.replace(".shx", ".sld")
        elif(tipe=="dbf"):
            sldPath = source.replace(".dbf", ".sld")
        sldPath = sldPath.replace("\\", "/")
        layer.saveSldStyle(sldPath)
        return sldPath
    

    def start_browse_metadata(self):
        filter = "XML files (*.xml)"
        filename1, _ = QFileDialog.getOpenFileName(None, "Import XML", "",filter)
        print(filename1)
        self.lineEdit_metadata.setText(filename1)
        self.pathMeta = filename1
        
    def start_browse_style(self):
        filter = "SLD files (*.sld)"
        filePath, _ = QFileDialog.getOpenFileName(None, "Import SLD", "",filter)
        print(filePath)
        self.lineEdit_style.setText(filePath)
        self.pathSLD = filePath

    # # upload Metadata
    # def uploadMetadata(self, Lid) :
    #     metadataPath = self.pathMeta
    #     filesMeta = {'file': open(metadataPath,'rb')}
    #     params = {"akses":"PUBLIC","identifier":Lid,"KODESIMPUL":self.simpulJaringan}
    #     urlMeta = self.url+"/api/meta/link"
    #     responseAPIMeta = requests.post(urlMeta,files=filesMeta,params=params)
    #     print (responseAPIMeta.text)
    #     #return responseAPIMeta.text
    #     responseAPIMetaJSON = json.loads(responseAPIMeta.text)
    #     # if(responseAPIMetaJSON['RTN']):
    #     #     self.report(self.label_statusMetadata, True, 'Metadata berhasil diunggah!')
    #     # else:
    #     #     self.report(self.label_statusMetadata, False, 'Metadata Gagal diunggah! : '+responseAPIMetaJSON['MSG'])

    # report upload
    def report(self, label, result, message):
        if result is True:
            label.setStyleSheet("color: white; background-color: #4AA252; border-radius: 4px;") 
        elif result == 'reset':
            label.setStyleSheet("background-color: none; border-radius: 4px;")
        elif result == 'caution':
            label.setStyleSheet("color: white; background-color: #F28F1E; border-radius: 4px;")
        else :
            label.setStyleSheet("color: white; background-color: #C4392A; border-radius: 4px;")
        label.setText(message)
    
    def reportReset(self):
        #self.report(self.label_statusSLD, 'reset', '')
        #self.report(self.label_statusLayer, 'reset', '')
        #self.report(self.label_statusMetadata, 'reset', '')
        #self.report(self.label_statusPublish, 'reset', '')
        self.report(self.label_statusbase, 'reset', '')

        

# class ThreadClass(QThread):
#     any_signal = pyqtSignal(int)
#     def __init__(self, parent=None):
#         super(ThreadClass, self).__init__(parent)
#         self.is_running = True
#     def run(self):
#         print('starting thread')
#         cnt=0
#         while (True):
#             cnt+=1
#             if cnt==99:cnt=0
#             time.sleep(0.01)
#             self.any_signal.emit(cnt) 
#     def stop(self):
#         self.is_running = False
#         print('stopping thread')
