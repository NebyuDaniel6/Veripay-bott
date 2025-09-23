import { serve } from "https://deno.land/std@0.168.0/http/server.ts"

const BOT_TOKEN = Deno.env.get('BOT_TOKEN') || '8450018011:AAHbrKSnGqDLb-t6WAI74RbjN8A7OZNQSSc'

// Global storage
const users: Record<number, any> = {}
const userStates: Record<number, string> = {}

enum UserState {
  IDLE = "idle",
  WAITING_NAME = "waiting_name",
  WAITING_PHONE = "waiting_phone",
  WAITING_RESTAURANT = "waiting_restaurant"
}

async function sendMessage(chatId: number, text: string, replyMarkup?: any) {
  const url = `https://api.telegram.org/bot${BOT_TOKEN}/sendMessage`
  const data = { chat_id: chatId, text: text, parse_mode: "Markdown", ...(replyMarkup && { reply_markup: replyMarkup }) }
  await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })
}

function getMainKeyboard() {
  return { inline_keyboard: [[{ text: "👨‍🍳 Register as Waiter", callback_data: "register_waiter" }], [{ text: "👨‍💼 Register as Admin", callback_data: "register_admin" }]] }
}

async function handleStart(chatId: number, userId: number) {
  if (users[userId] && users[userId].approved) {
    await sendMessage(chatId, `Welcome back! Role: ${users[userId].role}`)
  } else {
    await sendMessage(chatId, "🎉 **Welcome to VeriPay!** 🎉\n\nChoose your role:", getMainKeyboard())
  }
}

async function handleRegisterWaiter(chatId: number, userId: number) {
  userStates[userId] = UserState.WAITING_NAME
  users[userId] = { role: 'waiter' }
  await sendMessage(chatId, "👨‍🍳 **Waiter Registration**\n\nPlease provide your full name:")
}

async function handleRegisterAdmin(chatId: number, userId: number) {
  userStates[userId] = UserState.WAITING_NAME
  users[userId] = { role: 'admin' }
  await sendMessage(chatId, "👨‍💼 **Admin Registration**\n\nPlease provide your full name:")
}

async function handleTextMessage(chatId: number, userId: number, text: string) {
  const currentState = userStates[userId] || UserState.IDLE
  
  if (currentState === UserState.WAITING_NAME) {
    users[userId].name = text
    userStates[userId] = UserState.WAITING_PHONE
    await sendMessage(chatId, `Name: ${text}\n\nPlease provide your phone number:`)
  } else if (currentState === UserState.WAITING_PHONE) {
    users[userId].phone = text
    userStates[userId] = UserState.WAITING_RESTAURANT
    await sendMessage(chatId, `Name: ${users[userId].name}\nPhone: ${text}\n\nPlease provide the restaurant name:`)
  } else if (currentState === UserState.WAITING_RESTAURANT) {
    users[userId].restaurant_name = text
    users[userId].approved = true
    userStates[userId] = UserState.IDLE
    await sendMessage(chatId, `✅ **Registration Complete!**\n\nName: ${users[userId].name}\nPhone: ${users[userId].phone}\nRestaurant: ${text}\nRole: ${users[userId].role}\n\nYou are now registered and approved!`)
  } else {
    await sendMessage(chatId, "Please use the menu buttons or send /start to begin.")
  }
}

async function handleCallbackQuery(chatId: number, userId: number, callbackData: string) {
  if (callbackData === "register_waiter") {
    await handleRegisterWaiter(chatId, userId)
  } else if (callbackData === "register_admin") {
    await handleRegisterAdmin(chatId, userId)
  }
}

serve(async (req) => {
  if (req.method !== 'POST') return new Response(JSON.stringify({ error: 'Method not allowed' }), { status: 405, headers: { 'Content-Type': 'application/json' } })
  
  const webhookData = await req.json()
  
  if (webhookData.message) {
    const { chat, from, text } = webhookData.message
    if (text?.startsWith('/start')) {
      await handleStart(chat.id, from.id)
    } else {
      await handleTextMessage(chat.id, from.id, text || '')
    }
  } else if (webhookData.callback_query) {
    const { message, from, data } = webhookData.callback_query
    await handleCallbackQuery(message.chat.id, from.id, data)
  }
  
  return new Response(JSON.stringify({ status: 'success' }), { status: 200, headers: { 'Content-Type': 'application/json' } })
})
