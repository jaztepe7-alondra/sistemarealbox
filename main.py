
# ============================================================================
# ============================================================================
# ==================== REALBOX - SISTEMA DE CONTROL DE INVENTARIOS ==========
# ============================================================================
# Descripción: Aplicación para gestionar inventario de productos con Firebase
# Autor: Jazmin Alondra Tepetate Medina
# Versión: 2.4 - Corrección: Container scroll y usuarios especiales
# ============================================================================

# ==================== IMPORTACIÓN DE LIBRERÍAS ====================
import flet as ft                    # Librería para crear la interfaz gráfica
import pyrebase                      # Librería para conectar con Firebase
from datetime import datetime, timedelta  # Para manejar fechas y horas
from reportlab.lib.pagesizes import letter, landscape  # Tamaño de carta
from reportlab.lib import colors     # Colores para tablas en PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer  # Elementos PDF
from reportlab.lib.styles import getSampleStyleSheet  # Estilos de texto para PDF
import os                            # Para manejar rutas de archivos
import time                          # Para pausas temporales

# Importar la configuración de Firebase
from firebase_config import firebase_config

# ==================== INICIALIZAR FIREBASE ====================
firebase = pyrebase.initialize_app(firebase_config)
db = firebase.database()        # Base de datos Realtime Database
auth = firebase.auth()          # Sistema de autenticación

# ==================== FUNCIÓN PARA CALCULAR DÍAS DE ALERTA ====================
def calcular_dias_alerta(vida_util_dias):
    """
    Calcula cuántos días antes de la caducidad se debe activar la alerta
    
    Reglas:
    - 3 días → Alerta 2 días antes
    - 5 días → Alerta 3 días antes
    - 6-10 días → Alerta 4 días antes
    - 11-15 días → Alerta 7 días antes
    - 16+ días → Alerta 10 días antes
    """
    if vida_util_dias <= 3:
        return 2
    elif vida_util_dias == 5:
        return 3
    elif vida_util_dias >= 6 and vida_util_dias <= 10:
        return 4
    elif vida_util_dias >= 11 and vida_util_dias <= 15:
        return 7
    else:
        return 10

# ==================== FUNCIÓN PARA DETERMINAR ESTATUS ====================
def determinar_estatus(fecha_caducidad, vida_util_dias):
    """
    Determina si un producto está en estado NORMAL o ALERTA
    """
    fecha_actual = datetime.now()
    dias_para_alerta = calcular_dias_alerta(vida_util_dias)
    fecha_alerta = fecha_caducidad - timedelta(days=dias_para_alerta)
    
    if fecha_actual >= fecha_alerta:
        return "ALERTA"
    else:
        return "NORMAL"

# ==================== CLASE PRINCIPAL DE LA APP ====================
class RealBoxApp:
    """
    Clase principal que controla toda la aplicación REALBOX
    
    Tipos de usuario:
    - ASOCIADOe: Usuarios especiales (Edna y Jazmin)
    - ASOCIADOr: Usuarios con permiso para modificar productos base
    - ASOCIADO: Usuarios regulares
    """
    
    def __init__(self, page: ft.Page):
        """Constructor de la clase"""
        self.page = page
        self.page.title = "REALBOX - Control de Inventarios"
        self.page.theme_mode = ft.ThemeMode.LIGHT
        self.page.bgcolor = "#FFFFFF"
        self.page.window.width = 550
        self.page.window.height = 850
        self.page.scroll = ft.ScrollMode.AUTO
        
        # Variables de sesión
        self.usuario_actual = None
        self.tipo_usuario = None
        self.nombre_completo = None
        self.id_empleado = None
        
        # Usuarios especiales (ASOCIADOe)
        self.usuarios_especiales = {
            "741001": {"nombre": "Edna Patiño", "tipo": "ASOCIADOe"},
            "741002": {"nombre": "Jazmin Alondra Tepetate Medina", "tipo": "ASOCIADOe", "id": "000002"}
        }
        
        # Lista de asociados (se llena al abrir reporte)
        self.asociados_lista = []
        
        self.navegar_a_login()
    
    # ========================================================================
    # ==================== PANTALLA DE LOGIN ================================
    # ========================================================================
    
    def navegar_a_login(self):
        """Muestra la pantalla de inicio de sesión"""
        self.page.clean()
        
        self.login_id = ft.TextField(
            label="ID de Asociado",
            hint_text="Ej: 000001",
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.login_password = ft.TextField(
            label="Contraseña",
            password=True,
            can_reveal_password=True,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.login_error = ft.Text("", color=ft.colors.RED, size=12)
        
        login_btn = ft.ElevatedButton(
            "INICIAR SESIÓN",
            on_click=self.verificar_login,
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        registro_btn = ft.TextButton(
            "¿Primera vez? Regístrate aquí",
            on_click=self.navegar_a_registro,
            style=ft.ButtonStyle(color="#000000"),
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=50),
                        ft.Text("REALBOX", size=32, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Text("Control de Inventarios", size=16, color="#666666"),
                        ft.Container(height=50),
                        self.login_id,
                        self.login_password,
                        self.login_error,
                        ft.Container(height=20),
                        login_btn,
                        ft.Container(height=20),
                        registro_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    def verificar_login(self, e):
        """Valida las credenciales del usuario"""
        id_empleado = self.login_id.value.strip()
        password = self.login_password.value.strip()
        
        if not id_empleado or not password:
            self.login_error.value = "Ingrese ID y contraseña"
            self.page.update()
            return
        
        # Verificar usuarios especiales
        if password in self.usuarios_especiales:
            usuario_info = self.usuarios_especiales[password]
            
            if password == "741002":
                if id_empleado != "000002":
                    self.login_error.value = "ID incorrecto para esta contraseña"
                    self.page.update()
                    return
            
            self.usuario_actual = password
            self.tipo_usuario = usuario_info["tipo"]
            self.nombre_completo = usuario_info["nombre"]
            self.id_empleado = id_empleado if "id" in usuario_info else id_empleado
            self.navegar_a_menu_principal()
            return
        
        # Verificar usuarios en Firebase
        try:
            usuarios_ref = db.child("usuarios").child(id_empleado).get()
            
            if usuarios_ref.val():
                usuario_data = usuarios_ref.val()
                
                if usuario_data.get("password") == password:
                    self.usuario_actual = id_empleado
                    self.tipo_usuario = usuario_data.get("tipo", "ASOCIADO")
                    self.nombre_completo = usuario_data.get("nombre", "")
                    self.id_empleado = id_empleado
                    self.navegar_a_menu_principal()
                else:
                    self.login_error.value = "Contraseña incorrecta"
                    self.page.update()
            else:
                self.login_error.value = "Usuario no encontrado"
                self.page.update()
        except Exception as ex:
            self.login_error.value = f"Error: {str(ex)}"
            self.page.update()
    
    def navegar_a_registro(self, e):
        """Muestra formulario para registrar nuevos usuarios"""
        self.page.clean()
        
        self.registro_id = ft.TextField(
            label="ID de Asociado",
            hint_text="Ej: 000003",
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.registro_nombre = ft.TextField(
            label="Nombre Completo",
            hint_text="Nombre y apellidos",
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.registro_password = ft.TextField(
            label="Contraseña (6 números)",
            hint_text="Ej: 123456",
            password=True,
            max_length=6,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.registro_error = ft.Text("", color=ft.colors.RED, size=12)
        
        registro_btn = ft.ElevatedButton(
            "REGISTRARSE",
            on_click=self.registrar_usuario,
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        volver_btn = ft.TextButton(
            "Volver al inicio",
            on_click=lambda e: self.navegar_a_login(),
            style=ft.ButtonStyle(color="#000000"),
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=50),
                        ft.Text("REGISTRO", size=28, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Text("Nuevo Asociado", size=14, color="#666666"),
                        ft.Container(height=30),
                        self.registro_id,
                        self.registro_nombre,
                        self.registro_password,
                        self.registro_error,
                        ft.Container(height=20),
                        registro_btn,
                        ft.Container(height=20),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    def registrar_usuario(self, e):
        """Guarda un nuevo usuario en Firebase"""
        id_empleado = self.registro_id.value.strip()
        nombre = self.registro_nombre.value.strip()
        password = self.registro_password.value.strip()
        
        if not id_empleado or not nombre or not password:
            self.registro_error.value = "Complete todos los campos"
            self.page.update()
            return
        
        if len(password) != 6 or not password.isdigit():
            self.registro_error.value = "La contraseña debe ser de 6 números"
            self.page.update()
            return
        
        try:
            existente = db.child("usuarios").child(id_empleado).get()
            if existente.val():
                self.registro_error.value = "El ID ya está registrado"
                self.page.update()
                return
            
            usuario_data = {
                "id": id_empleado,
                "nombre": nombre,
                "password": password,
                "tipo": "ASOCIADO",
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            db.child("usuarios").child(id_empleado).set(usuario_data)
            
            self.registro_error.value = "¡Registro exitoso! Inicie sesión"
            self.registro_error.color = ft.colors.GREEN
            self.page.update()
            
            time.sleep(2)
            self.navegar_a_login()
            
        except Exception as ex:
            self.registro_error.value = f"Error: {str(ex)}"
            self.page.update()
    
    # ========================================================================
    # ==================== MENÚ PRINCIPAL ====================================
    # ========================================================================
    
    def navegar_a_menu_principal(self):
        """Muestra el menú principal"""
        self.page.clean()
        
        bienvenida = ft.Text(
            f"Bienvenido/a, {self.nombre_completo}",
            size=18,
            weight=ft.FontWeight.BOLD,
            color="#000000",
        )
        
        tipo_label = ft.Text(
            f"Tipo: {self.tipo_usuario}",
            size=14,
            color="#666666",
        )
        
        btn_producto_base = ft.ElevatedButton(
            "📦 REGISTRAR PRODUCTO BASE",
            on_click=lambda e: self.navegar_a_producto_base(),
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        btn_gestionar_base = None
        if self.tipo_usuario in ["ASOCIADOe", "ASOCIADOr"]:
            btn_gestionar_base = ft.ElevatedButton(
                "✏️ GESTIONAR PRODUCTOS BASE",
                on_click=lambda e: self.navegar_a_gestionar_productos_base(),
                bgcolor="#333333",
                color="#FFFFFF",
                width=300,
                height=50,
            )
        
        btn_registro_llegada = ft.ElevatedButton(
            "📥 INGRESAR REGISTRO DE LLEGADA",
            on_click=lambda e: self.navegar_a_registro_llegada(),
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        btn_inventario = ft.ElevatedButton(
            "📋 VER INVENTARIO",
            on_click=lambda e: self.navegar_a_inventario(),
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        btn_reporte = ft.ElevatedButton(
            "📄 GENERAR REPORTE PDF",
            on_click=lambda e: self.navegar_a_reporte(),
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        btn_actualizaciones = None
        if self.tipo_usuario == "ASOCIADOe" and self.id_empleado == "000001":
            btn_actualizaciones = ft.ElevatedButton(
                "🔧 ACTUALIZACIONES DEL SISTEMA",
                on_click=lambda e: self.navegar_a_actualizaciones(),
                bgcolor="#333333",
                color="#FFFFFF",
                width=300,
                height=50,
            )
        
        btn_permisos = None
        if self.tipo_usuario == "ASOCIADOe" and self.id_empleado == "000002":
            btn_permisos = ft.ElevatedButton(
                "👥 GESTIONAR PERMISOS",
                on_click=lambda e: self.navegar_a_gestion_permisos(),
                bgcolor="#333333",
                color="#FFFFFF",
                width=300,
                height=50,
            )
        
        btn_cerrar_sesion = ft.TextButton(
            "Cerrar sesión",
            on_click=lambda e: self.navegar_a_login(),
            style=ft.ButtonStyle(color="#000000"),
        )
        
        columnas = [
            ft.Container(height=30),
            bienvenida,
            tipo_label,
            ft.Container(height=30),
            btn_producto_base,
        ]
        
        if btn_gestionar_base:
            columnas.append(btn_gestionar_base)
        
        columnas.extend([
            btn_registro_llegada,
            btn_inventario,
            btn_reporte,
        ])
        
        if btn_actualizaciones:
            columnas.append(btn_actualizaciones)
        
        if btn_permisos:
            columnas.append(btn_permisos)
        
        columnas.extend([
            ft.Container(height=30),
            btn_cerrar_sesion,
        ])
        
        self.page.add(
            ft.Container(
                content=ft.Column(columnas, horizontal_alignment=ft.CrossAxisAlignment.CENTER, scroll=ft.ScrollMode.AUTO),
                padding=20,
            )
        )
    
    # ========================================================================
    # ==================== REGISTRAR PRODUCTO BASE ===========================
    # ========================================================================
    
    def navegar_a_producto_base(self):
        """Muestra formulario para registrar productos"""
        self.page.clean()
        
        self.prod_nombre = ft.TextField(
            label="Nombre del Producto",
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_id = ft.TextField(
            label="ID del Producto (Código de Barras)",
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_precio = ft.TextField(
            label="Precio Normal ($)",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_descuento = ft.TextField(
            label="Descuento en Alerta (%)",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_empaques = ft.TextField(
            label="Empaques por Caja",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_vida = ft.TextField(
            label="Tiempo de Vida (días)",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_error = ft.Text("", color=ft.colors.RED, size=12)
        self.prod_exito = ft.Text("", color=ft.colors.GREEN, size=12)
        
        guardar_btn = ft.ElevatedButton(
            "GUARDAR PRODUCTO",
            on_click=self.guardar_producto_base,
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        volver_btn = ft.TextButton(
            "Volver al menú",
            on_click=lambda e: self.navegar_a_menu_principal(),
            style=ft.ButtonStyle(color="#000000"),
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Text("REGISTRAR PRODUCTO BASE", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Container(height=20),
                        self.prod_nombre,
                        self.prod_id,
                        self.prod_precio,
                        self.prod_descuento,
                        self.prod_empaques,
                        self.prod_vida,
                        self.prod_error,
                        self.prod_exito,
                        ft.Container(height=20),
                        guardar_btn,
                        ft.Container(height=10),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    def guardar_producto_base(self, e):
        """Guarda un producto en Firebase"""
        nombre = self.prod_nombre.value.strip()
        producto_id = self.prod_id.value.strip()
        precio = self.prod_precio.value.strip()
        descuento = self.prod_descuento.value.strip()
        empaques = self.prod_empaques.value.strip()
        vida = self.prod_vida.value.strip()
        
        if not all([nombre, producto_id, precio, descuento, empaques, vida]):
            self.prod_error.value = "Complete todos los campos"
            self.page.update()
            return
        
        try:
            existente = db.child("productos_base").child(producto_id).get()
            
            if existente.val() and self.tipo_usuario == "ASOCIADO":
                self.prod_error.value = "Producto ya existe. Solo ASOCIADOr o ASOCIADOe pueden modificar"
                self.page.update()
                return
            
            producto_data = {
                "id": producto_id,
                "nombre": nombre,
                "precio": float(precio),
                "descuento": float(descuento),
                "empaques_por_caja": int(empaques),
                "vida_util_dias": int(vida),
                "fecha_registro": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "registrado_por": self.id_empleado,
                "registrado_nombre": self.nombre_completo,
            }
            
            db.child("productos_base").child(producto_id).set(producto_data)
            
            self.prod_exito.value = "¡Producto guardado exitosamente!"
            self.prod_error.value = ""
            self.page.update()
            
            self.prod_nombre.value = ""
            self.prod_id.value = ""
            self.prod_precio.value = ""
            self.prod_descuento.value = ""
            self.prod_empaques.value = ""
            self.prod_vida.value = ""
            self.page.update()
            
        except Exception as ex:
            self.prod_error.value = f"Error: {str(ex)}"
            self.page.update()
    
    # ========================================================================
    # ==================== GESTIONAR PRODUCTOS BASE ==========================
    # ========================================================================
    
    def navegar_a_gestionar_productos_base(self):
        """Muestra lista de productos para modificar/eliminar"""
        self.page.clean()
        
        titulo = ft.Text(
            "GESTIONAR PRODUCTOS BASE",
            size=20,
            weight=ft.FontWeight.BOLD,
            color="#000000",
        )
        
        descripcion = ft.Text(
            "Selecciona un producto para modificar o eliminar",
            size=12,
            color="#666666",
        )
        
        try:
            productos_ref = db.child("productos_base").get()
            productos_lista = []
            if productos_ref.val():
                for producto_id, data in productos_ref.val().items():
                    productos_lista.append({
                        "id": producto_id,
                        "nombre": data.get("nombre", ""),
                        "precio": data.get("precio", 0),
                        "datos": data
                    })
        except:
            productos_lista = []
        
        columnas = [
            ft.Container(height=20),
            titulo,
            descripcion,
            ft.Container(height=20),
        ]
        
        if productos_lista:
            for prod in productos_lista:
                producto_card = ft.Container(
                    content=ft.Row(
                        [
                            ft.Column(
                                [
                                    ft.Text(f"ID: {prod['id']}", weight=ft.FontWeight.BOLD, size=12),
                                    ft.Text(f"Nombre: {prod['nombre']}", size=11),
                                    ft.Text(f"Precio: ${prod['precio']:.2f}", size=11),
                                ],
                                expand=True,
                            ),
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.EDIT,
                                        tooltip="Modificar",
                                        on_click=lambda e, p=prod: self.editar_producto_base(p),
                                        icon_color="#000000",
                                    ),
                                    ft.IconButton(
                                        icon=ft.icons.DELETE,
                                        tooltip="Eliminar",
                                        on_click=lambda e, p=prod: self.eliminar_producto_base(p),
                                        icon_color=ft.colors.RED,
                                    ),
                                ],
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=10,
                    border=ft.border.all(1, ft.colors.BLACK),
                    border_radius=5,
                    margin=ft.margin.only(bottom=5),
                )
                columnas.append(producto_card)
        else:
            columnas.append(ft.Text("No hay productos registrados", color="#666666"))
        
        volver_btn = ft.ElevatedButton(
            "VOLVER AL MENÚ",
            on_click=lambda e: self.navegar_a_menu_principal(),
            bgcolor="#000000",
            color="#FFFFFF",
            width=200,
            height=40,
        )
        
        columnas.append(ft.Container(height=20))
        columnas.append(volver_btn)
        
        self.page.add(
            ft.Container(
                content=ft.Column(columnas, scroll=ft.ScrollMode.AUTO),
                padding=20,
            )
        )
    
    def editar_producto_base(self, producto):
        """Muestra formulario para editar producto"""
        self.page.clean()
        
        datos = producto["datos"]
        
        self.prod_edit_nombre = ft.TextField(
            label="Nombre del Producto",
            value=datos.get("nombre", ""),
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_edit_id = ft.TextField(
            label="ID del Producto",
            value=datos.get("id", ""),
            read_only=True,
            bgcolor="#E0E0E0",
            border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_edit_precio = ft.TextField(
            label="Precio Normal ($)",
            value=str(datos.get("precio", 0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_edit_descuento = ft.TextField(
            label="Descuento en Alerta (%)",
            value=str(datos.get("descuento", 0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_edit_empaques = ft.TextField(
            label="Empaques por Caja",
            value=str(datos.get("empaques_por_caja", 1)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_edit_vida = ft.TextField(
            label="Tiempo de Vida (días)",
            value=str(datos.get("vida_util_dias", 0)),
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.prod_edit_error = ft.Text("", color=ft.colors.RED, size=12)
        self.prod_edit_exito = ft.Text("", color=ft.colors.GREEN, size=12)
        
        guardar_btn = ft.ElevatedButton(
            "ACTUALIZAR PRODUCTO",
            on_click=lambda e: self.actualizar_producto_base(producto["id"]),
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        volver_btn = ft.TextButton(
            "Volver",
            on_click=lambda e: self.navegar_a_gestionar_productos_base(),
            style=ft.ButtonStyle(color="#000000"),
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Text("EDITAR PRODUCTO", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Container(height=20),
                        self.prod_edit_id,
                        self.prod_edit_nombre,
                        self.prod_edit_precio,
                        self.prod_edit_descuento,
                        self.prod_edit_empaques,
                        self.prod_edit_vida,
                        self.prod_edit_error,
                        self.prod_edit_exito,
                        ft.Container(height=20),
                        guardar_btn,
                        ft.Container(height=10),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    def actualizar_producto_base(self, producto_id):
        """Actualiza producto en Firebase"""
        nombre = self.prod_edit_nombre.value.strip()
        precio = self.prod_edit_precio.value.strip()
        descuento = self.prod_edit_descuento.value.strip()
        empaques = self.prod_edit_empaques.value.strip()
        vida = self.prod_edit_vida.value.strip()
        
        if not all([nombre, precio, descuento, empaques, vida]):
            self.prod_edit_error.value = "Complete todos los campos"
            self.page.update()
            return
        
        try:
            producto_data = {
                "id": producto_id,
                "nombre": nombre,
                "precio": float(precio),
                "descuento": float(descuento),
                "empaques_por_caja": int(empaques),
                "vida_util_dias": int(vida),
                "fecha_modificacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "modificado_por": self.id_empleado,
                "modificado_nombre": self.nombre_completo,
            }
            
            db.child("productos_base").child(producto_id).update(producto_data)
            
            self.prod_edit_exito.value = "¡Producto actualizado exitosamente!"
            self.prod_edit_error.value = ""
            self.page.update()
            
            time.sleep(2)
            self.navegar_a_gestionar_productos_base()
            
        except Exception as ex:
            self.prod_edit_error.value = f"Error: {str(ex)}"
            self.page.update()
    
    def eliminar_producto_base(self, producto):
        """Elimina producto de Firebase"""
        def confirmar_eliminacion(e):
            try:
                db.child("productos_base").child(producto["id"]).remove()
                self.navegar_a_gestionar_productos_base()
            except Exception as ex:
                ft.AlertDialog(
                    title=ft.Text("Error"),
                    content=ft.Text(f"No se pudo eliminar: {str(ex)}"),
                    actions=[ft.TextButton("Aceptar", on_click=lambda e: dlg.close())],
                )
        
        dlg = ft.AlertDialog(
            title=ft.Text("¿Eliminar producto?"),
            content=ft.Text(f"¿Estás seguro de eliminar '{producto['nombre']}' (ID: {producto['id']})?"),
            actions=[
                ft.TextButton("Cancelar", on_click=lambda e: dlg.close()),
                ft.TextButton("Eliminar", on_click=confirmar_eliminacion, style=ft.ButtonStyle(color=ft.colors.RED)),
            ],
        )
        
        self.page.dialog = dlg
        dlg.open = True
        self.page.update()
    
    # ========================================================================
    # ==================== REGISTRO DE LLEGADA ===============================
    # ========================================================================
    
    def navegar_a_registro_llegada(self):
        """Muestra formulario para registrar llegada de productos"""
        self.page.clean()
        
        try:
            productos_ref = db.child("productos_base").get()
            self.productos_lista = []
            if productos_ref.val():
                for producto_id, data in productos_ref.val().items():
                    self.productos_lista.append({
                        "id": producto_id,
                        "nombre": data.get("nombre", ""),
                        "precio": data.get("precio", 0),
                    })
        except:
            self.productos_lista = []
        
        self.llegada_producto = ft.Dropdown(
            label="Seleccionar Producto",
            options=[ft.dropdown.Option(p["id"], p["nombre"]) for p in self.productos_lista],
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
            on_change=self.actualizar_info_producto,
        )
        
        self.llegada_cajas = ft.TextField(
            label="Cantidad de Cajas",
            keyboard_type=ft.KeyboardType.NUMBER,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.llegada_info = ft.Text("", color="#666666", size=12)
        self.llegada_error = ft.Text("", color=ft.colors.RED, size=12)
        self.llegada_exito = ft.Text("", color=ft.colors.GREEN, size=12)
        
        guardar_btn = ft.ElevatedButton(
            "REGISTRAR LLEGADA",
            on_click=self.guardar_registro_llegada,
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        volver_btn = ft.TextButton(
            "Volver al menú",
            on_click=lambda e: self.navegar_a_menu_principal(),
            style=ft.ButtonStyle(color="#000000"),
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Text("INGRESAR REGISTRO DE LLEGADA", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Container(height=20),
                        self.llegada_producto,
                        self.llegada_info,
                        self.llegada_cajas,
                        self.llegada_error,
                        self.llegada_exito,
                        ft.Container(height=20),
                        guardar_btn,
                        ft.Container(height=10),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    def actualizar_info_producto(self, e):
        """Muestra información del producto seleccionado"""
        producto_id = self.llegada_producto.value
        for p in self.productos_lista:
            if p["id"] == producto_id:
                self.llegada_info.value = f"Producto: {p['nombre']} | Precio: ${p['precio']}"
                self.page.update()
                break
    
    def guardar_registro_llegada(self, e):
        """Guarda registro de llegada en Firebase"""
        producto_id = self.llegada_producto.value
        cajas = self.llegada_cajas.value.strip()
        
        if not producto_id or not cajas:
            self.llegada_error.value = "Seleccione producto y cantidad de cajas"
            self.page.update()
            return
        
        try:
            producto_ref = db.child("productos_base").child(producto_id).get()
            if not producto_ref.val():
                self.llegada_error.value = "Producto no encontrado"
                self.page.update()
                return
            
            producto_data = producto_ref.val()
            cajas_int = int(cajas)
            empaques_por_caja = producto_data.get("empaques_por_caja", 1)
            vida_util = producto_data.get("vida_util_dias", 0)
            
            fecha_registro = datetime.now()
            fecha_caducidad = fecha_registro + timedelta(days=vida_util)
            estatus = determinar_estatus(fecha_caducidad, vida_util)
            
            precio_normal = producto_data.get("precio", 0)
            descuento = producto_data.get("descuento", 0)
            precio_con_descuento = precio_normal * (1 - descuento / 100)
            
            registro_data = {
                "producto_id": producto_id,
                "producto_nombre": producto_data.get("nombre", ""),
                "cajas": cajas_int,
                "empaques_totales": cajas_int * empaques_por_caja,
                "precio_normal": precio_normal,
                "descuento": descuento,
                "precio_con_descuento": precio_con_descuento,
                "fecha_registro": fecha_registro.strftime("%Y-%m-%d %H:%M:%S"),
                "fecha_caducidad": fecha_caducidad.strftime("%Y-%m-%d"),
                "vida_util_dias": vida_util,
                "estatus": estatus,
                "id_asociado": self.id_empleado,
                "nombre_asociado": self.nombre_completo,
            }
            
            registro_id = f"{producto_id}_{fecha_registro.strftime('%Y%m%d%H%M%S')}"
            db.child("inventario").child(registro_id).set(registro_data)
            
            self.llegada_exito.value = "¡Registro de llegada guardado exitosamente!"
            self.llegada_error.value = ""
            self.page.update()
            
            self.llegada_producto.value = None
            self.llegada_cajas.value = ""
            self.llegada_info.value = ""
            self.page.update()
            
        except Exception as ex:
            self.llegada_error.value = f"Error: {str(ex)}"
            self.page.update()
    
    # ========================================================================
    # ✅ CORREGIDO: VER INVENTARIO (SIN scroll EN Container) =================
    # ========================================================================
    
    def navegar_a_inventario(self):
        """
        Muestra tabla con todos los registros de inventario
        ✅ CORREGIDO: Se usa Column con scroll en lugar de Container
        """
        self.page.clean()
        
        filtro_estatus = ft.Dropdown(
            label="Filtrar por Estatus",
            options=[
                ft.dropdown.Option("todos", "Todos los productos"),
                ft.dropdown.Option("NORMAL", "Solo NORMAL"),
                ft.dropdown.Option("ALERTA", "Solo ALERTA"),
            ],
            value="todos",
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
            on_change=lambda e: self.cargar_inventario(e.control.value),
        )
        
        btn_refrescar = ft.IconButton(
            icon=ft.icons.REFRESH,
            tooltip="Refrescar",
            on_click=lambda e: self.cargar_inventario(filtro_estatus.value),
            icon_color="#000000",
        )
        
        self.inventario_container = ft.Container()
        
        volver_btn = ft.ElevatedButton(
            "VOLVER AL MENÚ",
            on_click=lambda e: self.navegar_a_menu_principal(),
            bgcolor="#000000",
            color="#FFFFFF",
            width=200,
            height=40,
        )
        
        # ✅ CORREGIDO: Usar Column con scroll en lugar de Container con scroll
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Text("INVENTARIO", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Container(height=10),
                        ft.Row([filtro_estatus, btn_refrescar], alignment=ft.MainAxisAlignment.CENTER),
                        ft.Container(height=20),
                        # ✅ Column con scroll para la tabla
                        ft.Container(
                            content=ft.Column(
                                [self.inventario_container],
                                scroll=ft.ScrollMode.AUTO  # ✅ scroll EN Column, NO en Container
                            ),
                            width=self.page.window.width - 60,
                            height=450,
                        ),
                        ft.Container(height=20),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
        
        self.cargar_inventario("todos")
    
    def cargar_inventario(self, filtro_estatus):
        """Carga y muestra el inventario con el filtro seleccionado"""
        try:
            inventario_ref = db.child("inventario").get()
            registros = []
            if inventario_ref.val():
                for registro_id, data in inventario_ref.val().items():
                    if filtro_estatus != "todos":
                        if data.get("estatus", "").upper() != filtro_estatus.upper():
                            continue
                    registros.append(data)
        except:
            registros = []
        
        if not registros:
            self.inventario_container.content = ft.Text(
                "No hay registros en el inventario",
                size=16,
                color="#666666",
            )
            self.page.update()
            return
        
        cabecera = [
            "Asociado", "Producto", "Fecha Registro", "Caducidad", 
            "Estatus", "Precio Normal", "Precio Descuento"
        ]
        
        filas = []
        for reg in registros:
            estatus = reg.get("estatus", "")
            
            bgcolor_fila = None
            color_texto = "#000000"
            
            if estatus.upper() == "ALERTA":
                bgcolor_fila = "#FFCDD2"
                color_texto = "#C62828"
            else:
                bgcolor_fila = "#FFFFFF"
            
            # Verificar ambas claves para compatibilidad
            nombre_asociado = reg.get("nombre_asociado", reg.get("nombre_empleado", ""))
            
            fila = ft.DataRow(
                color=ft.colors.with_opacity(0, bgcolor_fila if bgcolor_fila else "#FFFFFF"),
                cells=[
                    ft.DataCell(ft.Text(nombre_asociado[:15], color=color_texto, size=9)),
                    ft.DataCell(ft.Text(reg.get("producto_nombre", "")[:15], color=color_texto, size=9)),
                    ft.DataCell(ft.Text(reg.get("fecha_registro", "")[:10], color=color_texto, size=9)),
                    ft.DataCell(ft.Text(reg.get("fecha_caducidad", ""), color=color_texto, size=9)),
                    ft.DataCell(ft.Text(estatus, color=color_texto, size=9, weight=ft.FontWeight.BOLD)),
                    ft.DataCell(ft.Text(f"${reg.get('precio_normal', 0):.2f}", color=color_texto, size=9)),
                    ft.DataCell(ft.Text(f"${reg.get('precio_con_descuento', 0):.2f}", color=color_texto, size=9)),
                ],
            )
            filas.append(fila)
        
        tabla = ft.DataTable(
            columns=[ft.DataColumn(ft.Text(c, size=10, weight=ft.FontWeight.BOLD)) for c in cabecera],
            rows=filas,
            heading_row_color=ft.colors.BLACK12,
            border=ft.border.all(1, ft.colors.BLACK),
            column_spacing=10,
        )
        
        self.inventario_container.content = tabla
        self.page.update()
    
    # ========================================================================
    # ✅ CORREGIDO: GENERAR REPORTE PDF CON USUARIOS ESPECIALES ==============
    # ========================================================================
    
    def navegar_a_reporte(self):
        """
        Muestra opciones para generar reporte en PDF
        ✅ INCLUYE USUARIOS ESPECIALES (Edna y Jazmin)
        """
        self.page.clean()
        
        # ✅ CARGAR TODOS LOS ASOCIADOS (Firebase + Especiales)
        try:
            usuarios_ref = db.child("usuarios").get()
            self.asociados_lista = []
            
            # Agregar usuarios especiales primero (Edna y Jazmin)
            for password, info in self.usuarios_especiales.items():
                self.asociados_lista.append({
                    "id": info.get("id", password),
                    "nombre": info["nombre"],
                    "tipo": info["tipo"]
                })
            
            # Agregar usuarios de Firebase
            if usuarios_ref.val():
                for assoc_id, data in usuarios_ref.val().items():
                    # Evitar duplicados
                    existe = False
                    for assoc in self.asociados_lista:
                        if assoc["id"] == assoc_id:
                            existe = True
                            break
                    
                    if not existe:
                        self.asociados_lista.append({
                            "id": assoc_id,
                            "nombre": data.get("nombre", ""),
                            "tipo": data.get("tipo", "ASOCIADO")
                        })
            
            print(f"✅ Total de asociados cargados: {len(self.asociados_lista)}")
            for assoc in self.asociados_lista:
                print(f"   - {assoc['nombre']} (ID: {assoc['id']}, Tipo: {assoc['tipo']})")
                
        except Exception as ex:
            print(f"❌ Error cargando asociados: {ex}")
            self.asociados_lista = []
        
        self.reporte_tipo = ft.Dropdown(
            label="Tipo de Reporte",
            options=[
                ft.dropdown.Option("completo", "Completo"),
                ft.dropdown.Option("fecha", "Por Fecha"),
                ft.dropdown.Option("asociado", "Por Asociado"),
                ft.dropdown.Option("estatus", "Por Estatus"),
            ],
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
            on_change=self.actualizar_opciones_reporte,
        )
        
        self.reporte_filtro_dropdown = ft.Dropdown(
            label="Seleccionar Filtro",
            visible=False,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.reporte_filtro_text = ft.TextField(
            label="Filtro (Fecha/Estatus)",
            hint_text="Depende del tipo de reporte",
            visible=False,
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.reporte_error = ft.Text("", color=ft.colors.RED, size=12)
        self.reporte_exito = ft.Text("", color=ft.colors.GREEN, size=12)
        
        generar_btn = ft.ElevatedButton(
            "GENERAR PDF",
            on_click=self.generar_reporte_pdf,
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        volver_btn = ft.TextButton(
            "Volver al menú",
            on_click=lambda e: self.navegar_a_menu_principal(),
            style=ft.ButtonStyle(color="#000000"),
        )
        
        self.reporte_filtro_dropdown.options = []
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Text("GENERAR REPORTE PDF", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Container(height=20),
                        self.reporte_tipo,
                        self.reporte_filtro_dropdown,
                        self.reporte_filtro_text,
                        self.reporte_error,
                        self.reporte_exito,
                        ft.Container(height=20),
                        generar_btn,
                        ft.Container(height=10),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    def actualizar_opciones_reporte(self, e):
        """Actualiza los controles de filtro según el tipo de reporte"""
        tipo = self.reporte_tipo.value
        
        self.reporte_filtro_dropdown.visible = False
        self.reporte_filtro_text.visible = False
        self.reporte_filtro_dropdown.options = []
        
        if tipo == "fecha":
            self.reporte_filtro_text.visible = True
            self.reporte_filtro_text.label = "Seleccionar Fecha"
            self.reporte_filtro_text.hint_text = "Ej: 2025-01-15"
        
        elif tipo == "asociado":
            self.reporte_filtro_dropdown.visible = True
            self.reporte_filtro_dropdown.label = "Seleccionar Asociado"
            
            if self.asociados_lista:
                self.reporte_filtro_dropdown.options = [
                    ft.dropdown.Option(assoc["id"], f"{assoc['nombre']} (ID: {assoc['id']})")
                    for assoc in self.asociados_lista
                ]
                print(f"✅ Dropdown actualizado con {len(self.asociados_lista)} asociados")
            else:
                self.reporte_filtro_dropdown.options = [
                    ft.dropdown.Option("sin_datos", "No hay asociados registrados")
                ]
        
        elif tipo == "estatus":
            self.reporte_filtro_dropdown.visible = True
            self.reporte_filtro_dropdown.label = "Seleccionar Estatus"
            self.reporte_filtro_dropdown.options = [
                ft.dropdown.Option("NORMAL", "NORMAL"),
                ft.dropdown.Option("ALERTA", "ALERTA"),
            ]
        
        self.page.update()
    
    def generar_reporte_pdf(self, e):
        """Genera archivo PDF con los datos del inventario filtrados"""
        tipo = self.reporte_tipo.value
        
        if self.reporte_filtro_dropdown.visible and self.reporte_filtro_dropdown.value:
            filtro = self.reporte_filtro_dropdown.value
        elif self.reporte_filtro_text.visible and self.reporte_filtro_text.value:
            filtro = self.reporte_filtro_text.value.strip()
        else:
            filtro = ""
        
        print(f"📊 Generando reporte tipo: {tipo}, filtro: {filtro}")
        
        try:
            inventario_ref = db.child("inventario").get()
            registros = []
            if inventario_ref.val():
                for registro_id, data in inventario_ref.val().items():
                    if tipo == "fecha" and filtro:
                        if filtro not in data.get("fecha_registro", ""):
                            continue
                    elif tipo == "asociado" and filtro:
                        id_asociado = data.get("id_asociado", data.get("id_empleado", ""))
                        nombre_asociado = data.get("nombre_asociado", data.get("nombre_empleado", ""))
                        
                        if filtro not in id_asociado and filtro not in nombre_asociado:
                            continue
                    elif tipo == "estatus" and filtro:
                        if filtro.upper() != data.get("estatus", "").upper():
                            continue
                    registros.append(data)
            
            print(f"✅ Registros encontrados: {len(registros)}")
            
            if not registros:
                self.reporte_error.value = "No hay registros para el reporte"
                self.page.update()
                return
            
            nombre_archivo = f"reporte_realbox_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            ruta_archivo = os.path.join(os.getcwd(), nombre_archivo)
            
            doc = SimpleDocTemplate(ruta_archivo, pagesize=landscape(letter))
            elementos = []
            estilos = getSampleStyleSheet()
            
            titulo = Paragraph("REALBOX - Reporte de Inventario", estilos["Heading1"])
            elementos.append(titulo)
            elementos.append(Spacer(1, 20))
            
            info = f"Tipo: {tipo.upper()} | Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')} | Registros: {len(registros)}"
            elementos.append(Paragraph(info, estilos["Normal"]))
            elementos.append(Spacer(1, 20))
            
            datos_tabla = [["Asociado", "Producto", "Fecha", "Caducidad", "Estatus", "P. Normal", "P. Descuento"]]
            for reg in registros:
                nombre_asociado = reg.get("nombre_asociado", reg.get("nombre_empleado", "N/A"))
                
                datos_tabla.append([
                    nombre_asociado[:20],
                    reg.get("producto_nombre", "")[:20],
                    reg.get("fecha_registro", "")[:10],
                    reg.get("fecha_caducidad", ""),
                    reg.get("estatus", ""),
                    f"${reg.get('precio_normal', 0):.2f}",
                    f"${reg.get('precio_con_descuento', 0):.2f}",
                ])
            
            tabla = Table(datos_tabla, colWidths=[90, 90, 75, 75, 65, 70, 70])
            
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.black),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            
            elementos.append(tabla)
            doc.build(elementos)
            
            self.reporte_exito.value = f"PDF generado: {nombre_archivo}"
            self.reporte_error.value = ""
            self.page.update()
            
        except Exception as ex:
            print(f"❌ Error generando PDF: {ex}")
            self.reporte_error.value = f"Error: {str(ex)}"
            self.page.update()
    
    # ========================================================================
    # ==================== ACTUALIZACIONES DEL SISTEMA =======================
    # ========================================================================
    
    def navegar_a_actualizaciones(self):
        """Muestra historial de actualizaciones (Solo Edna)"""
        self.page.clean()
        
        try:
            actualizaciones_ref = db.child("actualizaciones").get()
            actualizaciones = []
            if actualizaciones_ref.val():
                for key, data in actualizaciones_ref.val().items():
                    actualizaciones.append(data)
        except:
            actualizaciones = []
        
        lista_actualizaciones = ft.Column([], scroll=ft.ScrollMode.AUTO, height=400)
        
        if actualizaciones:
            for act in actualizaciones:
                lista_actualizaciones.controls.append(
                    ft.Container(
                        content=ft.Column([
                            ft.Text(act.get("titulo", "Sin título"), weight=ft.FontWeight.BOLD, size=14),
                            ft.Text(act.get("descripcion", ""), size=12),
                            ft.Text(f"Fecha: {act.get('fecha', '')}", size=10, color="#666666"),
                            ft.Divider(),
                        ]),
                        padding=10,
                    )
                )
        else:
            lista_actualizaciones.controls.append(
                ft.Text("No hay actualizaciones registradas", color="#666666")
            )
        
        volver_btn = ft.ElevatedButton(
            "VOLVER AL MENÚ",
            on_click=lambda e: self.navegar_a_menu_principal(),
            bgcolor="#000000",
            color="#FFFFFF",
            width=200,
            height=40,
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Text("ACTUALIZACIONES DEL SISTEMA", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Text("Solo para ASOCIADOe - Edna", size=12, color="#666666"),
                        ft.Container(height=20),
                        lista_actualizaciones,
                        ft.Container(height=20),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    # ========================================================================
    # ==================== GESTIONAR PERMISOS ================================
    # ========================================================================
    
    def navegar_a_gestion_permisos(self):
        """Permite conceder permisos de ASOCIADOr (Solo Jazmin)"""
        self.page.clean()
        
        self.permisos_id = ft.TextField(
            label="ID del Asociado a conceder permiso",
            bgcolor="#F5F5F5",
            border_color="#000000",
            focused_border_color="#000000",
            label_style=ft.TextStyle(color="#000000"),
        )
        
        self.permisos_error = ft.Text("", color=ft.colors.RED, size=12)
        self.permisos_exito = ft.Text("", color=ft.colors.GREEN, size=12)
        
        conceder_btn = ft.ElevatedButton(
            "CONCEDER PERMISO ASOCIADOr",
            on_click=self.conceder_permiso,
            bgcolor="#000000",
            color="#FFFFFF",
            width=300,
            height=50,
        )
        
        volver_btn = ft.TextButton(
            "Volver al menú",
            on_click=lambda e: self.navegar_a_menu_principal(),
            style=ft.ButtonStyle(color="#000000"),
        )
        
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Container(height=20),
                        ft.Text("GESTIONAR PERMISOS", size=20, weight=ft.FontWeight.BOLD, color="#000000"),
                        ft.Text("Solo para ASOCIADOe - Jazmin", size=12, color="#666666"),
                        ft.Container(height=20),
                        ft.Text("Concede permiso para modificar/eliminar productos base", size=12, color="#666666"),
                        ft.Container(height=20),
                        self.permisos_id,
                        self.permisos_error,
                        self.permisos_exito,
                        ft.Container(height=20),
                        conceder_btn,
                        ft.Container(height=10),
                        volver_btn,
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=20,
            )
        )
    
    def conceder_permiso(self, e):
        """Actualiza el tipo de usuario a ASOCIADOr"""
        empleado_id = self.permisos_id.value.strip()
        
        if not empleado_id:
            self.permisos_error.value = "Ingrese ID del asociado"
            self.page.update()
            return
        
        try:
            usuario_ref = db.child("usuarios").child(empleado_id).get()
            if not usuario_ref.val():
                self.permisos_error.value = "Usuario no encontrado"
                self.page.update()
                return
            
            db.child("usuarios").child(empleado_id).update({"tipo": "ASOCIADOr"})
            
            self.permisos_exito.value = f"Permiso concedido a {empleado_id}"
            self.permisos_error.value = ""
            self.page.update()
            
        except Exception as ex:
            self.permisos_error.value = f"Error: {str(ex)}"
            self.page.update()
# ==================== FUNCIÓN PRINCIPAL ====================
def main(page: ft.Page):
    """Función de entrada de la aplicación"""
    app = RealBoxApp(page)

# ==================== INICIAR APLICACIÓN PARA RENDER ====================
if __name__ == "__main__":
    import os
    # Render asigna un puerto automáticamente en la variable PORT
    port = int(os.environ.get("PORT", 8550))
    
    # Ejecutar Flet en modo web server, escuchando en todas las interfaces
    ft.app(
        target=main, 
        view=ft.WEB_BROWSER, 
        port=port, 
        host="0.0.0.0"
    )
    

