# 🚀 VAPI Workflow - Todo Empanadas

## ✅ **LO QUE YA ESTÁ LISTO**
- ✅ Backend API funcionando en: `https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app`
- ✅ Endpoints de carrito, menú y checkout operacionales
- ✅ Firebase integration activa 
- ✅ Test de integración pasando (script en `tests/test_checkout_flow.py`)

## 🎯 **PASOS PARA PROBAR EN VAPI**

### **OPCIÓN 1: Prueba Rápida (5 min)**
1. **Ve a VAPI Dashboard** → Create Assistant
2. **System Prompt**: Copia el contenido de `vapi_config/system_prompt.md`
3. **Añadir solo 3 funciones esenciales**:
   - `getFullMenuX` (GET /menu)
   - `addToCart` (POST /cart/add) 
   - `checkoutCart` (POST /cart/{session_id}/checkout)
4. **Test**: Habla → "Quiero hacer un pedido" → Debería llamar las funciones

### **OPCIÓN 2: Configuración Completa**
- Sigue la guía paso a paso en `vapi_config/setup_instructions.md`
- Configura las 7 funciones completas

## 📋 **FUNCTION CALLS RÁPIDAS**

### **getFullMenuX**
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/menu
Method: GET
Parameters: none
```

### **addToCart**
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/cart/add
Method: POST
Body: {
  "session_id": "{{call.id}}",
  "item_id": "main1",
  "quantity": 1
}
```

### **checkoutCart**
```
URL: https://vapivoiceagent-qka8o83cy-juberths-projects.vercel.app/cart/{{call.id}}/checkout
Method: POST
Body: {
  "customer_name": "{{customer_name}}",
  "customer_phone": "{{customer_phone}}"
}
```

## 🎯 **FLUJO DE PRUEBA**
1. **"Hola"** → Saludo de Natalia
2. **"Quiero hacer un pedido"** → Debe preguntar pickup/delivery
3. **"Para recoger"** → Debe pedir nombre/teléfono
4. **"Juan, 555-1234"** → Debe mostrar menú (`getFullMenuX`)
5. **"Quiero salmón"** → Debe añadir (`addToCart` con `main1`)
6. **"Finalizar pedido"** → Debe hacer checkout (`checkoutCart`)

## 🔧 **MENÚ ACTUAL (para testing)**
- `main1`: Grilled Salmon ($24.99)
- `main2`: Ribeye Steak ($32.99)  
- `main3`: Chicken Parmesan ($19.99)
- `dess1`: Tiramisu ($7.99)

## 🚀 **SIGUIENTE PASO**
1. Configura en VAPI con las 3 funciones básicas
2. Haz una llamada de prueba
3. Verifica que las funciones se ejecuten
4. ¡Reporta cómo fue la experiencia!

## 🆘 **TROUBLESHOOTING**
- **Function no se ejecuta**: Verificar URL y method
- **Error 404**: Asegurar que la URL no tenga `/api/main` extra
- **Session ID**: Usar `{{call.id}}` en VAPI
- **Test manual**: Usar `python3 tests/test_checkout_flow.py` para verificar backend

---
**¿Listo para probarlo?** Configura en VAPI y cuéntame cómo va! 🎉 