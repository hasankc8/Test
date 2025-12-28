import sys
import datetime
import pymongo
from pymongo.errors import ConnectionFailure
from PyQt5.QtWidgets import (QApplication, QMainWindow, QMessageBox, QTableWidgetItem,
                             QHeaderView, QInputDialog, QLineEdit, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from main_ui import Ui_FitWithFlux

class DatabaseManager:
    def __init__(self):
        self.client = None
        self.db = None
        self.users = None
        self.plans = None
        self.connect()

    def connect(self):
        try:
            self.client = pymongo.MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=3000)
            self.client.server_info()

            self.db = self.client["FitWithFluxDB"]
            self.users = self.db["users"]
            self.plans = self.db["plans"]
            print("Veritabanı: BAĞLANDI ✅")
            return True
        except ConnectionFailure:
            print("Veritabanı: BAĞLANTI HATASI ❌ (MongoDB Servisi açık mı?)")
            return False

    def register_user(self, username, email, password, sec_q, sec_a):
        if self.users.find_one({"$or": [{"username": username}, {"email": email}]}):
            return False, "Bu kullanıcı adı veya e-mail zaten kayıtlı."

        user_data = {
            "username": username,
            "email": email,
            "password": password,
            "security_question": sec_q,
            "security_answer": sec_a
        }
        self.users.insert_one(user_data)
        return True, "Kayıt Başarılı!"

    def check_login(self, username, password):
        return self.users.find_one({"username": username, "password": password})

    def save_plan(self, plan_data):
        try:
            self.plans.update_one(
                {"owner": plan_data["owner"], "name": plan_data["name"]},
                {"$set": plan_data},
                upsert=True
            )
            return True
        except Exception as e:
            print(f"Kayıt Hatası: {e}")
            return False

    def get_user_plans(self, username):
        return list(self.plans.find({"owner": username}))

    def delete_plan(self, username, plan_name):
        self.plans.delete_one({"owner": username, "name": plan_name})

    def get_single_plan(self, username, plan_name):
        return self.plans.find_one({"owner": username, "name": plan_name})

    def get_user_by_username(self, username):
        return self.users.find_one({"username": username})

    def update_password(self, username, new_pass):
        self.users.update_one({"username": username}, {"$set": {"password": new_pass}})

class FitnessApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_FitWithFlux()
        self.ui.setupUi(self)
        self.db = DatabaseManager()
        self.current_user = None
        self.temp_analysis_data = {}

        self.ui.lineEdit_kilo.setPlaceholderText("Kilo (Kg)")
        self.ui.lineEdit_password.setEchoMode(QLineEdit.Password)
        self.ui.lineEdit_sifreolusturma.setEchoMode(QLineEdit.Normal)
        self.ui.lineEdit_yeniSifre.setEchoMode(QLineEdit.Normal)

        self.lbl_hosgeldin = QLabel(self.ui.coklu_Menu)
        self.lbl_hosgeldin.setStyleSheet("color: #E25822; font-size: 32px; font-weight: 900; background: transparent;")
        self.lbl_hosgeldin.setAlignment(Qt.AlignCenter)
        self.lbl_hosgeldin.setText("")

        try:
            self.ui.gridLayout.addWidget(self.lbl_hosgeldin, 0, 0, 1, 4)
        except:
            self.lbl_hosgeldin.setGeometry(50, 20, 700, 60)

        self.ui.tableWidget_haftalikMenu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.tableWidget_PlanTablosu.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.ui.stackedWidget.setCurrentIndex(0)

        self.baglantilari_kur()

    def baglantilari_kur(self):
        self.ui.pushButton_kaydol.clicked.connect(lambda: self.nav(1))
        self.ui.pushButton_sifremiUnuttum.clicked.connect(lambda: self.nav(2))
        self.ui.pushButton_girisyapgeri.clicked.connect(lambda: self.nav(0))
        self.ui.pushButton_girisedon.clicked.connect(lambda: self.nav(0))
        self.ui.pushButton_planOlustur.clicked.connect(lambda: self.nav(4))
        self.ui.pushButton_planlarim.clicked.connect(self.planlari_yukle_ve_git)
        self.ui.pushButton_cikismenu.clicked.connect(self.cikis_yap)
        self.ui.pushButton_geriPlanolustur.clicked.connect(lambda: self.nav(3))
        self.ui.Button_anaMenuPlankismi.clicked.connect(lambda: self.nav(3))
        self.ui.pushButton_cikis_plan_olustur.clicked.connect(self.cikis_yap)
        self.ui.pushButton_AnaMenuAnalizveMenu.clicked.connect(lambda: self.nav(3))
        self.ui.Button_geriPlanveMenu.clicked.connect(lambda: self.nav(4))
        self.ui.pushButton_anaMenuPlanlarim.clicked.connect(lambda: self.nav(3))
        self.ui.pushButton_geriPlanlarim.clicked.connect(lambda: self.nav(3))
        self.ui.pushButton_geriCikis.clicked.connect(self.cikis_yap)
        self.ui.pushButton_gerimenu.clicked.connect(self.cikis_yap)

        self.ui.pushButton_entry.clicked.connect(self.giris_yap)
        self.ui.pushButton_kaydolmaTamamla.clicked.connect(self.kayit_ol)
        self.ui.pushButton_sorgula.clicked.connect(self.sifre_sifirla)
        self.ui.pushButton_AnalizEt.clicked.connect(self.hesapla)
        self.ui.pushButton_PlankaydetveMenuolustur.clicked.connect(self.kaydet_ve_menu_olustur)
        self.ui.pushButton_VerileriGuncelle.clicked.connect(self.verileri_duzenle_git)
        self.ui.pushButton_MenuGuncelle.clicked.connect(self.menuyu_guncelle_kaydet)
        self.ui.pushButton.clicked.connect(self.plani_sil)
        self.ui.tableWidget_PlanTablosu.cellDoubleClicked.connect(self.plani_ac)

    def nav(self, index):
        self.ui.stackedWidget.setCurrentIndex(index)

    def mesaj_goster(self, baslik, icerik, icon=QMessageBox.Information):
        msg = QMessageBox()
        msg.setWindowTitle(baslik)
        msg.setText(icerik)
        msg.setIcon(icon)
        msg.setStyleSheet("background-color: #222; color: white;")
        msg.exec_()

    def giris_yap(self):
        u = self.ui.lineEdit_userName.text()
        p = self.ui.lineEdit_password.text()

        user = self.db.check_login(u, p)
        if user:
            self.current_user = u
            self.lbl_hosgeldin.setText(f"HOŞGELDİN {u.upper()}")
            self.mesaj_goster("Başarılı", f"Hoşgeldin {u}!")
            self.nav(3)
        else:
            self.mesaj_goster("Hata", "Kullanıcı adı veya şifre yanlış.", QMessageBox.Warning)

    def kayit_ol(self):
        u = self.ui.lineEdit_kaydolma_userName.text()
        e = self.ui.lineEdit_email.text()
        p = self.ui.lineEdit_sifreolusturma.text()
        sq = self.ui.comboBox_securityquestion.currentText()
        sa = self.ui.lineEdit_answerofquestion.text()

        if u and e and p and sa:
            durum, mesaj = self.db.register_user(u, e, p, sq, sa)
            self.mesaj_goster("Bilgi", mesaj)
            if durum: self.nav(0)
        else:
            self.mesaj_goster("Uyarı", "Lütfen tüm alanları doldurun.", QMessageBox.Warning)

    def cikis_yap(self):
        self.current_user = None
        self.lbl_hosgeldin.clear()
        self.ui.lineEdit_userName.clear()
        self.ui.lineEdit_password.clear()
        self.nav(0)

    def sifre_sifirla(self):
        kullanici_adi, ok = QInputDialog.getText(self, "Kullanıcı Adı", "Kullanıcı adınızı girin:")
        if not ok or not kullanici_adi: return

        user = self.db.get_user_by_username(kullanici_adi)
        if not user:
            self.mesaj_goster("Hata", "Kullanıcı bulunamadı.", QMessageBox.Critical)
            return

        cevap = self.ui.lineEdit_emailrepeat.text()
        yeni_sifre = self.ui.lineEdit_yeniSifre.text()

        if cevap == user.get("security_answer"):
            if yeni_sifre:
                self.db.update_password(kullanici_adi, yeni_sifre)
                self.mesaj_goster("Başarılı", "Şifreniz güncellendi.")
                self.nav(0)
            else:
                self.mesaj_goster("Hata", "Yeni şifre boş olamaz.", QMessageBox.Warning)
        else:
            self.mesaj_goster("Hata", "Güvenlik sorusu cevabı yanlış!", QMessageBox.Critical)

    def hesapla(self):
        try:
            kilo = float(self.ui.lineEdit_kilo.text())
            boy = float(self.ui.lineEdit_Boy.text())
            yas = int(self.ui.lineEdit_Yas.text())
            cinsiyet = self.ui.comboBox_cinsiyet.currentText()
            hedef = self.ui.comboBox_hedef.currentText()
            akt_text = self.ui.comboBox_AktiviteDuzey.currentText()

            boy_m = boy / 100
            bmi = kilo / (boy_m ** 2)

            if cinsiyet == "Erkek":
                bmr = (10 * kilo) + (6.25 * boy) - (5 * yas) + 5
            else:
                bmr = (10 * kilo) + (6.25 * boy) - (5 * yas) - 161

            carpanlar = {"Hareketsiz": 1.2, "Haftada 1-2 gün": 1.375, "Haftada 3-4 gün": 1.55, "Haftada 5-6gün": 1.725}
            tdee = bmr * carpanlar.get(akt_text, 1.2)

            hedef_kalori = tdee
            if hedef == "Yağ yakma":
                hedef_kalori -= 500
            elif hedef == "Kas yapma":
                hedef_kalori += 400

            su = kilo * 0.033

            self.ui.label_BMI.setText(f"BMI: {bmi:.1f}")
            self.ui.label_BMR.setText(f"BMR: {int(bmr)}")
            self.ui.label_TDEE.setText(f"TDEE: {int(tdee)}")
            self.ui.label_HedefKalori.setText(f"Hedef: {int(hedef_kalori)}")
            self.ui.label_Su.setText(f"Su: {su:.1f} Lt")

            durum = "Normal"
            if bmi < 18.5:
                durum = "Zayıf"
            elif bmi > 25:
                durum = "Fazla Kilolu"
            self.ui.label_Durum.setText(f"Durum:\n{durum}")

            self.temp_analysis_data = {
                "weight": kilo, "height": boy, "age": yas, "gender": cinsiyet, "activity": akt_text,
                "bmi": f"{bmi:.1f}", "bmr": int(bmr), "tdee": int(tdee),
                "target": int(hedef_kalori), "water": f"{su:.1f}",
                "goal": hedef, "status": durum,
                "date": datetime.datetime.now().strftime("%Y-%m-%d")
            }
            return True

        except ValueError:
            self.mesaj_goster("Hata", "Lütfen Kilo, Boy ve Yaş alanlarına SAYI giriniz.", QMessageBox.Warning)
            return False

    def varsayilan_menu_getir(self, kalori):
        if kalori < 1800:
            return ["Yumurta, Lor", "Izgara Tavuk, Salata", "Sebze Yemeği"]
        elif kalori < 2500:
            return ["Yulaf, Süt, Muz", "Köfte, Bulgur, Ayran", "Et Sote, Salata"]
        else:
            return ["3 Yumurta, Peynir", "Tavuklu Pilav", "Makarna, Ton Balığı"]

    def kaydet_ve_menu_olustur(self):
        if not self.hesapla(): return

        plan_adi = self.ui.lineEdit_planAdi.text()
        if not plan_adi:
            self.mesaj_goster("Hata", "Lütfen plan adı giriniz.", QMessageBox.Warning);
            return

        hedef_kalori = self.temp_analysis_data["target"]
        yemekler = self.varsayilan_menu_getir(hedef_kalori)

        menu_content = {}
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        for gun in gunler:
            menu_content[gun] = {"Sabah": yemekler[0], "Öğle": yemekler[1], "Akşam": yemekler[2]}

        final_data = {
            "owner": self.current_user,
            "name": plan_adi,
            "menu": menu_content,
            **self.temp_analysis_data
        }

        if self.db.save_plan(final_data):
            self.sayfa5_sonuclari_doldur(final_data)
            self.mesaj_goster("Başarılı", "Plan kaydedildi!")
            self.nav(5)
        else:
            self.mesaj_goster("Hata", "Kayıt başarısız.", QMessageBox.Critical)

    def sayfa5_sonuclari_doldur(self, data):
        self.ui.label_planAdi.setText(data.get("name", "-"))
        self.ui.label_hedefbuyukYazi.setText(f"HEDEF: {data.get('target')} kcal")
        self.ui.label_BMIAnalizveMenu.setText(f"BMI: {data.get('bmi')}")
        self.ui.label_su_ihtiyaci.setText(f"Su: {data.get('water')} Lt")
        self.ui.label_BMRvucutAnaliz.setText(f"BMR: {data.get('bmr')}")
        self.ui.label_TDEEvucutAnaliz.setText(f"TDEE: {data.get('tdee')}")
        self.ui.label_VUCUTdurumu.setText(f"Durum: {data.get('status')}")

        menu = data.get("menu", {})
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]

        self.ui.tableWidget_haftalikMenu.clearContents()
        for col_idx, gun in enumerate(gunler):
            gun_menu = menu.get(gun, {})
            items = [gun_menu.get("Sabah", ""), gun_menu.get("Öğle", ""), gun_menu.get("Akşam", "")]

            for row_idx, yemek_adi in enumerate(items):
                item = QTableWidgetItem(yemek_adi)
                item.setTextAlignment(Qt.AlignCenter)
                item.setForeground(QColor("#FF4500"))
                self.ui.tableWidget_haftalikMenu.setItem(row_idx, col_idx, item)

        self.temp_analysis_data = data

    def menuyu_guncelle_kaydet(self):
        if not self.temp_analysis_data: return
        gunler = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
        yeni_menu = {}
        for col, gun in enumerate(gunler):
            yeni_menu[gun] = {
                "Sabah": self.ui.tableWidget_haftalikMenu.item(0, col).text() if self.ui.tableWidget_haftalikMenu.item(
                    0, col) else "",
                "Öğle": self.ui.tableWidget_haftalikMenu.item(1, col).text() if self.ui.tableWidget_haftalikMenu.item(1,
                                                                                                                      col) else "",
                "Akşam": self.ui.tableWidget_haftalikMenu.item(2, col).text() if self.ui.tableWidget_haftalikMenu.item(
                    2, col) else ""
            }
        self.temp_analysis_data["menu"] = yeni_menu
        self.db.save_plan(self.temp_analysis_data)
        self.mesaj_goster("Başarılı", "Menü değişiklikleri kaydedildi.")

    def verileri_duzenle_git(self):
        data = self.temp_analysis_data
        if not data: return
        self.ui.lineEdit_planAdi.setText(data.get("name", ""))
        self.ui.lineEdit_kilo.setText(str(data.get("weight", "")))
        self.ui.lineEdit_Boy.setText(str(data.get("height", "")))
        self.ui.lineEdit_Yas.setText(str(data.get("age", "")))
        self.ui.comboBox_cinsiyet.setCurrentText(data.get("gender", "Erkek"))
        self.ui.comboBox_hedef.setCurrentText(data.get("goal", "Form"))
        self.ui.comboBox_AktiviteDuzey.setCurrentText(data.get("activity", "Hareketsiz"))
        self.nav(4)

    def planlari_yukle_ve_git(self):
        self.ui.tableWidget_PlanTablosu.setRowCount(0)
        planlar = self.db.get_user_plans(self.current_user)
        for i, plan in enumerate(planlar):
            self.ui.tableWidget_PlanTablosu.insertRow(i)
            self.ui.tableWidget_PlanTablosu.setItem(i, 0, QTableWidgetItem(plan.get("date", "-")))
            self.ui.tableWidget_PlanTablosu.setItem(i, 1, QTableWidgetItem(plan.get("name", "-")))
            self.ui.tableWidget_PlanTablosu.setItem(i, 2, QTableWidgetItem(plan.get("goal", "-")))
            self.ui.tableWidget_PlanTablosu.setItem(i, 3, QTableWidgetItem(str(plan.get("target", "-"))))
        self.nav(6)

    def plani_ac(self, row, col):
        plan_adi = self.ui.tableWidget_PlanTablosu.item(row, 1).text()
        plan = self.db.get_single_plan(self.current_user, plan_adi)
        if plan:
            self.sayfa5_sonuclari_doldur(plan)
            self.nav(5)

    def plani_sil(self):
        row = self.ui.tableWidget_PlanTablosu.currentRow()
        if row >= 0:
            plan_adi = self.ui.tableWidget_PlanTablosu.item(row, 1).text()
            soru = QMessageBox.question(self, "Sil", f"{plan_adi} silinsin mi?", QMessageBox.Yes | QMessageBox.No)
            if soru == QMessageBox.Yes:
                self.db.delete_plan(self.current_user, plan_adi)
                self.ui.tableWidget_PlanTablosu.removeRow(row)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FitnessApp()
    window.show()
    sys.exit(app.exec_())