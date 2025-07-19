# Configuración VAPI - Todo Empanadas

## 🚀 PASOS PARA CONFIGURAR EN VAPI

### 1. **Crear Nuevo Assistant**
- Ve a tu dashboard de VAPI
- Click en "Create Assistant"
- Selecciona "Custom Assistant"

### 2. **Configuración Básica**
```
Name: Todo Empanadas - Natalia
Description: Recepcionista virtual para pedidos de empanadas
Language: Spanish (es-MX)
Voice: Nova (o la voz en español de tu preferencia)
```

### 3. **System Prompt**
- Copia el contenido de `system_prompt.md`
- Pégalo en el campo "System Message"

### 4. **Configurar Functions**
- En la sección "Functions", click "Add Function"
- Para cada función en `functions.json`:
  1. **Name**: Nombre de la función (ej: `getFullMenuX`)
  2. **Description**: Descripción de la función  
  3. **Parameters**: Copia el objeto `parameters`
  4. **Server Configuration**:
     - **URL**: URL del endpoint
     - **Method**: Método HTTP (GET/POST)
     - **Headers**: `Content-Type: application/json`
     - **Body**: Para POST requests, copia el objeto `body`

### 5. **Funciones a Configurar**

#### 5.1 `getFullMenuX`
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/menu
Method: GET
Parameters: {} (vacío)
```

#### 5.2 `getMenuCategory`
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/menu/{{category}}
Method: GET
Parameters: { "category": "string" }
```

#### 5.3 `addToCart`
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/cart/add
Method: POST
Headers: Content-Type: application/json
Body: {
  "session_id": "{{session_id}}",
  "item_id": "{{item_id}}",
  "quantity": "{{quantity}}",
  "special_requests": "{{special_requests}}"
}
```

#### 5.4 `getCartX`
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/cart/{{session_id}}
Method: GET
```

#### 5.5 `removeFromCart`
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/cart/remove
Method: POST
Body: {
  "session_id": "{{session_id}}",
  "item_id": "{{item_id}}"
}
```

#### 5.6 `checkoutCart`
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/cart/{{session_id}}/checkout
Method: POST
Body: {
  "customer_name": "{{customer_name}}",
  "customer_phone": "{{customer_phone}}",
  "special_instructions": "{{special_instructions}}"
}
```

### 6. **Variables de Sesión**
En VAPI, para pasar el session_id, usa:
- Variable: `{{call.id}}` (ID único de la llamada)
- Esto se mapea automáticamente al `session_id` en las funciones

### 7. **Configuración Adicional**
```
Max Duration: 10 minutes
Interruption Enabled: true
First Message: "¡Todo Empanadas, sucursal Magma en Monterrey! Le atiende Natalia. ¿En qué puedo ayudarle?"
End Call Phrases: ["gracias", "hasta luego", "adiós"]
```

### 8. **Testing**
1. Click en "Test" en el dashboard
2. Prueba el flujo:
   - Saludo inicial
   - "Quiero hacer un pedido"
   - Pedir mostrar el menú: `getFullMenuX`
   - Añadir item: `addToCart`
   - Ver carrito: `getCartX`
   - Checkout: `checkoutCart`

## 🔧 ITEMS DEL MENÚ ACTUAL
Para las pruebas, usa estos IDs:

**Appetizers:**
- `app1`: Bruschetta ($8.99)
- `app2`: Calamari Rings ($12.99)

**Mains:**
- `main1`: Grilled Salmon ($24.99)
- `main2`: Ribeye Steak ($32.99)
- `main3`: Chicken Parmesan ($19.99)

**Desserts:**
- `dess1`: Tiramisu ($7.99)
- `dess2`: Chocolate Lava Cake ($8.99)

## ⚠️ NOTAS IMPORTANTES
1. **Session ID**: VAPI debe pasar `{{call.id}}` como `session_id`
2. **Timeout**: Configura timeouts de 10s para las funciones
3. **Error Handling**: Si una función falla, el assistant debe disculparse y continuar
4. **Testing**: Usa el script `tests/test_checkout_flow.py` para verificar la funcionalidad

## 🚀 PRÓXIMOS PASOS
1. Configurar el assistant en VAPI
2. Hacer pruebas con llamadas de test
3. Actualizar `menu.json` con el menú real de empanadas
4. Ajustar el system prompt según sea necesario 