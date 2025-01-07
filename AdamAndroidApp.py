import threading
import cv2
import paramiko
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.graphics.texture import Texture


class SSHClient:
    def __init__(self, host, port, username, password):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = None
        self.running_commands = {}

    def connect(self):
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(self.host, self.port, self.username, self.password)

    def execute_command(self, command, command_name=None):
        if not self.client:
            raise Exception("Not connected")
        stdin, stdout, stderr = self.client.exec_command(command, get_pty=True)
        if command_name:
            self.running_commands[command_name] = stdin.channel

    def stop_command(self, command_name):
        if command_name in self.running_commands:
            self.running_commands[command_name].close()
            del self.running_commands[command_name]

    def disconnect(self):
        for channel in self.running_commands.values():
            channel.close()
        self.running_commands.clear()
        if self.client:
            self.client.close()


class AdamAndroidApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.language = 'ru'  # По умолчанию русский

    def build(self):
        self.ssh_client = SSHClient("192.168.50.10", 22, "adam", "adam1234")
        self.running_scripts = {}
        self.camera_active = False
        self.camera_thread = None
        self.camera_url = "http://192.168.50.10:18000/stream/0.mjpeg"
        self.stop_camera_flag = False

        root = BoxLayout(orientation='vertical', spacing=5, padding=1)

        # Верхняя панель кнопок управления камерой
        camera_control_layout = BoxLayout(size_hint=(1, 0.1), spacing=1)
        root.add_widget(camera_control_layout)

        start_camera_button = Button(text=self.translate("Запуск камеры"), size_hint=(0.5, 1))
        start_camera_button.bind(on_press=self.start_camera)
        camera_control_layout.add_widget(start_camera_button)

        stop_camera_button = Button(text=self.translate("Остановка камеры"), size_hint=(0.5, 1))
        stop_camera_button.bind(on_press=self.stop_camera)
        camera_control_layout.add_widget(stop_camera_button)

        # Скрипты управления
        script_control_layout = GridLayout(cols=2, size_hint=(1, 0.14), padding=1, spacing=1)
        self.add_script_buttons(script_control_layout)
        root.add_widget(script_control_layout)

        # Камера для отображения видео
        self.image = Image(size_hint=(1, 0.5))
        root.add_widget(self.image)

        # Кнопка переключения языка
        switch_language_button = Button(text=self.translate("Переключить язык"), size_hint=(1, 0.1))
        switch_language_button.bind(on_press=self.switch_language)
        root.add_widget(switch_language_button)

        # Кнопка для перезагрузки
        reboot_button = Button(text=self.translate("Перезагрузить АДАМ"), size_hint=(1, 0.1))
        reboot_button.bind(on_press=self.confirm_reboot)
        root.add_widget(reboot_button)




        return root

    def translate(self, text):
        translations = {
            'ru': {
                "Запуск камеры": "Start Camera",
                "Остановка камеры": "Stop Camera",
                "Перезагрузить АДАМ": "Reboot ADAM",
                "Переключить язык": "Switch Language",
                "Старт сервер": "Start Server",
                "Старт клиент": "Start Client",
                "Старт джойстик": "Start Joystick",
                "Остановить все": "Stop All",
                "Вы уверены, что хотите перезагружать систему?": "Are you sure you want to reboot the system?",
                "Подтверждение": "Confirmation",
                "Да": "Yes",
                "Нет": "No"
            },
            'en': {
                "Start Camera": "Запуск камеры",
                "Stop Camera": "Остановка камеры",
                "Reboot ADAM": "Перезагрузить АДАМ",
                "Switch Language": "Переключить язык",
                "Start Server": "Старт сервер",
                "Start Client": "Старт клиент",
                "Start Joystick": "Старт джойстик",
                "Stop All": "Остановить все",
                "Are you sure you want to reboot the system?": "Вы уверены, что хотите перезагружать систему?",
                "Confirmation": "Подтверждение",
                "Yes": "Да",
                "No": "Нет"
            }
        }
        return translations[self.language].get(text, text)

    def switch_language(self, instance):
        if self.language == 'ru':
            self.language = 'en'
        elif self.language == 'en':
            self.language = 'ru'
        self.update_ui()

    def update_ui(self):
        # Перезагружаем интерфейс с новым языком
        for child in self.root.children:
            if isinstance(child, BoxLayout):
                for button in child.children:
                    if isinstance(button, Button):
                        button.text = self.translate(button.text)
            elif isinstance(child, GridLayout):
                for button in child.children:
                    if isinstance(button, Button):
                        button.text = self.translate(button.text)

    def add_script_buttons(self, layout):
        # Команды для запуска скриптов
        self.commands = {
            self.translate("Старт сервер"): "source /home/adam/Venv/pre-default/bin/activate; python3 /home/adam/adam/AdamAiRpi/AdmAiServer/AdmAiServer.py",
            self.translate("Старт клиент"): "source /home/adam/Venv/pre-default/bin/activate; python3 /home/adam/adam/AdamAiRpi/AdmAiClient/AdmAiClient.py",
            self.translate("Старт джойстик"): "source /home/adam/Venv/pre-default/bin/activate; python3 /home/adam/adam/JoyStick.py",
        }

        for label, command in self.commands.items():
            button = Button(text=label, size_hint=(1, None), height=50)
            button.bind(on_press=lambda instance, cmd=command, name=label: self.start_script(cmd, name))
            layout.add_widget(button)

        stop_all_button = Button(text=self.translate("Остановить все"), size_hint=(1, None), height=50)
        stop_all_button.bind(on_press=self.stop_all_scripts)
        layout.add_widget(stop_all_button)

    def confirm_reboot(self, instance):
        # Создаем окно подтверждения
        layout = GridLayout(cols=1, padding=10, spacing=10)
        layout.add_widget(Label(text=self.translate("Вы уверены, что хотите перезагружать систему?")))

        button_layout = BoxLayout(size_hint=(1, 0.3), spacing=10)
        yes_button = Button(text=self.translate("Да"))
        no_button = Button(text=self.translate("Нет"))

        button_layout.add_widget(yes_button)
        button_layout.add_widget(no_button)
        layout.add_widget(button_layout)

        popup = Popup(title=self.translate("Подтверждение"), content=layout, size_hint=(0.8, 0.4))

        # Обработчики кнопок
        yes_button.bind(on_press=lambda x: self.reboot_system(popup))
        no_button.bind(on_press=popup.dismiss)

        popup.open()

    def reboot_system(self, popup):
        try:
            self.ssh_client.connect()
            self.ssh_client.execute_command("sudo reboot")
            print("Система перезагружается...")
        except Exception as e:
            print(f"Ошибка перезагрузки: {e}")
        finally:
            popup.dismiss()

    def start_camera(self, instance):
        if self.camera_active:
            print("Камера уже запущена")
            return
        self.camera_active = True
        self.stop_camera_flag = False
        self.camera_thread = threading.Thread(target=self.stream_camera)
        self.camera_thread.start()

    def stop_camera(self, instance):
        if not self.camera_active:
            print("Камера не запущена")
            return
        self.camera_active = False
        self.stop_camera_flag = True
        self.camera_thread.join()

    def stream_camera(self):
        capture = cv2.VideoCapture(self.camera_url)
        while not self.stop_camera_flag:
            ret, frame = capture.read()
            if not ret:
                print("Ошибка захвата кадра")
                break
            texture = self.create_texture(frame)
            self.image.texture = texture
        capture.release()

    def create_texture(self, frame):
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='rgb')
        texture.blit_buffer(frame.tobytes(), colorfmt='rgb', bufferfmt='ubyte')
        return texture

    def start_script(self, command, script_name):
        print(f"Запуск скрипта: {script_name}")
        self.ssh_client.connect()
        self.ssh_client.execute_command(command, script_name)

    def stop_all_scripts(self, instance):
        print("Остановка всех скриптов")
        for command_name in list(self.ssh_client.running_commands.keys()):
            self.ssh_client.stop_command(command_name)
        print("Все скрипты остановлены")


if __name__ == "__main__":
    AdamAndroidApp().run()
