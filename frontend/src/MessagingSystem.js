import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from './components/ui/dialog';
import { Switch } from './components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { toast } from './hooks/use-toast';
import { 
  MessageCircle, 
  Send, 
  Image, 
  Video, 
  Music, 
  DollarSign, 
  Eye, 
  Clock,
  Shield,
  Gift,
  Search,
  MoreVertical,
  Lock,
  Unlock
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const WS_URL = BACKEND_URL.replace('https://', 'wss://').replace('http://', 'ws://');

const MessagingSystem = ({ user }) => {
  const [conversations, setConversations] = useState([]);
  const [selectedConversation, setSelectedConversation] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [websocket, setWebsocket] = useState(null);
  const [onlineUsers, setOnlineUsers] = useState(new Set());
  const messagesEndRef = useRef(null);

  // Message creation state
  const [messageForm, setMessageForm] = useState({
    type: 'text',
    content: '',
    file: null,
    is_ppv: false,
    ppv_price: '',
    ppv_preview: '',
    is_tip: false,
    tip_amount: '',
    auto_destruct_minutes: null
  });

  // PPV payment modal
  const [showPPVModal, setShowPPVModal] = useState(false);
  const [selectedPPVMessage, setSelectedPPVMessage] = useState(null);

  useEffect(() => {
    if (user) {
      fetchConversations();
      initializeWebSocket();
    }

    return () => {
      if (websocket) {
        websocket.close();
      }
    };
  }, [user]);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const initializeWebSocket = () => {
    if (!user) return;

    const ws = new WebSocket(`${WS_URL}/ws/${user.id}`);
    
    ws.onopen = () => {
      console.log('WebSocket connected');
      setWebsocket(ws);
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'new_message') {
        // Add new message to current conversation if it matches
        if (selectedConversation && data.message.conversation_id === selectedConversation.id) {
          setMessages(prev => [...prev, data.message]);
        }
        
        // Update conversations list
        fetchConversations();
        
        // Show notification if not in current conversation
        if (!selectedConversation || data.message.conversation_id !== selectedConversation.id) {
          toast({
            title: "Nuevo mensaje",
            description: "Has recibido un nuevo mensaje"
          });
        }
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      // Attempt to reconnect after 3 seconds
      setTimeout(() => {
        if (user) {
          initializeWebSocket();
        }
      }, 3000);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  };

  const fetchConversations = async () => {
    try {
      const response = await axios.get(`${API}/conversations`);
      setConversations(response.data);
    } catch (error) {
      console.error('Error fetching conversations:', error);
      toast({
        title: "Error",
        description: "Error al cargar conversaciones",
        variant: "destructive"
      });
    }
  };

  const fetchMessages = async (conversationId) => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/conversations/${conversationId}/messages`);
      setMessages(response.data.messages);
    } catch (error) {
      console.error('Error fetching messages:', error);
      toast({
        title: "Error",
        description: "Error al cargar mensajes",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const selectConversation = (conversation) => {
    setSelectedConversation(conversation);
    fetchMessages(conversation.id);
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() && !messageForm.file) return;

    try {
      setLoading(true);
      
      if (messageForm.file) {
        // Send file message
        const formData = new FormData();
        formData.append('conversation_id', selectedConversation.id);
        formData.append('message_type', messageForm.type);
        formData.append('is_ppv', messageForm.is_ppv);
        formData.append('ppv_price', messageForm.ppv_price || '0');
        formData.append('ppv_preview', messageForm.ppv_preview || '');
        formData.append('auto_destruct_minutes', messageForm.auto_destruct_minutes || '');
        formData.append('file', messageForm.file);

        await axios.post(`${API}/messages/upload`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
      } else {
        // Send text message
        await axios.post(`${API}/messages/send`, {
          conversation_id: selectedConversation.id,
          message_type: 'text',
          content: newMessage,
          is_ppv: messageForm.is_ppv,
          ppv_price: messageForm.ppv_price ? parseFloat(messageForm.ppv_price) : null,
          ppv_preview: messageForm.ppv_preview,
          is_tip: messageForm.is_tip,
          tip_amount: messageForm.tip_amount ? parseFloat(messageForm.tip_amount) : null,
          auto_destruct_minutes: messageForm.auto_destruct_minutes
        });
      }

      // Reset form
      setNewMessage('');
      setMessageForm({
        type: 'text',
        content: '',
        file: null,
        is_ppv: false,
        ppv_price: '',
        ppv_preview: '',
        is_tip: false,
        tip_amount: '',
        auto_destruct_minutes: null
      });

      // Messages will be updated via WebSocket
    } catch (error) {
      console.error('Error sending message:', error);
      toast({
        title: "Error",
        description: "Error al enviar mensaje",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      // Determine message type based on file type
      let messageType = 'image';
      if (file.type.startsWith('video/')) {
        messageType = 'video';
      } else if (file.type.startsWith('audio/')) {
        messageType = 'audio';
      }

      setMessageForm({
        ...messageForm,
        file: file,
        type: messageType
      });
    }
  };

  const payForPPVMessage = async (message) => {
    try {
      const response = await axios.post(`${API}/messages/${message.id}/pay`);
      
      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      toast({
        title: "Error",
        description: "Error al procesar el pago",
        variant: "destructive"
      });
    }
  };

  const formatTime = (dateString) => {
    return new Date(dateString).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  const filteredConversations = conversations.filter(conv =>
    conv.other_user.full_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    conv.other_user.username.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const renderMessage = (message) => {
    const isOwn = message.sender_id === user.id;
    const isPPV = message.is_ppv && !isOwn;
    const showPPVPreview = isPPV && message.ppv_preview;

    return (
      <div key={message.id} className={`mb-4 flex ${isOwn ? 'justify-end' : 'justify-start'}`}>
        <div className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
          isOwn 
            ? 'bg-indigo-600 text-white' 
            : 'bg-white border border-slate-200 text-slate-900'
        }`}>
          {/* Message content */}
          {message.message_type === 'text' && (
            <div>
              {isPPV && !showPPVPreview ? (
                <div className="space-y-2">
                  <div className="flex items-center text-yellow-600">
                    <Lock className="h-4 w-4 mr-1" />
                    <span className="text-sm font-medium">Contenido Premium</span>
                  </div>
                  <p className="text-xs text-slate-600">
                    Paga ${message.ppv_price} para ver este mensaje
                  </p>
                  <Button 
                    size="sm" 
                    onClick={() => payForPPVMessage(message)}
                    className="w-full"
                  >
                    <DollarSign className="h-3 w-3 mr-1" />
                    Pagar ${message.ppv_price}
                  </Button>
                </div>
              ) : (
                <div>
                  {showPPVPreview && (
                    <div className="mb-2 p-2 bg-yellow-50 rounded text-xs">
                      <strong>Vista previa:</strong> {message.ppv_preview}
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => payForPPVMessage(message)}
                        className="mt-1 w-full"
                      >
                        Ver completo - ${message.ppv_price}
                      </Button>
                    </div>
                  )}
                  <p>{message.content}</p>
                </div>
              )}
            </div>
          )}

          {message.message_type !== 'text' && (
            <div className="space-y-2">
              <div className="flex items-center">
                {message.message_type === 'image' && <Image className="h-4 w-4 mr-1" />}
                {message.message_type === 'video' && <Video className="h-4 w-4 mr-1" />}
                {message.message_type === 'audio' && <Music className="h-4 w-4 mr-1" />}
                <span className="text-sm capitalize">{message.message_type}</span>
              </div>
              
              {isPPV ? (
                <div>
                  <p className="text-xs text-slate-600 mb-2">
                    Contenido premium - ${message.ppv_price}
                  </p>
                  <Button 
                    size="sm" 
                    onClick={() => payForPPVMessage(message)}
                  >
                    <Eye className="h-3 w-3 mr-1" />
                    Ver contenido
                  </Button>
                </div>
              ) : (
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => window.open(`${API}/messages/${message.id}/file`, '_blank')}
                >
                  <Eye className="h-3 w-3 mr-1" />
                  Ver {message.message_type}
                </Button>
              )}
            </div>
          )}

          {/* Tip indicator */}
          {message.is_tip && (
            <div className="mt-2 flex items-center text-green-600">
              <Gift className="h-3 w-3 mr-1" />
              <span className="text-xs">Propina: ${message.tip_amount}</span>
            </div>
          )}

          {/* Auto-destruct indicator */}
          {message.auto_destruct_at && (
            <div className="mt-1 flex items-center text-red-500">
              <Clock className="h-3 w-3 mr-1" />
              <span className="text-xs">Se autodestruye</span>
            </div>
          )}

          {/* Timestamp */}
          <div className={`text-xs mt-1 ${isOwn ? 'text-indigo-200' : 'text-slate-500'}`}>
            {formatTime(message.created_at)}
          </div>
        </div>
      </div>
    );
  };

  if (!user) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <MessageCircle className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-slate-900 mb-4">Inicia Sesión</h1>
        <p className="text-slate-600">Necesitas iniciar sesión para acceder a los mensajes</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Mensajes</h1>
        <p className="text-slate-600">Comunícate directamente con creadores y fans</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[600px]">
        {/* Conversations List */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="flex items-center">
              <MessageCircle className="h-5 w-5 mr-2" />
              Conversaciones
            </CardTitle>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 h-4 w-4" />
              <Input
                placeholder="Buscar conversaciones..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
          </CardHeader>
          <CardContent className="p-0">
            <div className="overflow-y-auto h-[450px]">
              {filteredConversations.length === 0 ? (
                <div className="p-4 text-center text-slate-500">
                  <MessageCircle className="h-8 w-8 mx-auto mb-2 text-slate-300" />
                  <p className="text-sm">No hay conversaciones</p>
                </div>
              ) : (
                filteredConversations.map(conversation => (
                  <div
                    key={conversation.id}
                    onClick={() => selectConversation(conversation)}
                    className={`p-4 border-b border-slate-100 cursor-pointer hover:bg-slate-50 ${
                      selectedConversation?.id === conversation.id ? 'bg-indigo-50' : ''
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Avatar>
                        <AvatarImage src={conversation.other_user.avatar_url} />
                        <AvatarFallback>
                          {conversation.other_user.full_name.substring(0, 2).toUpperCase()}
                        </AvatarFallback>
                      </Avatar>
                      
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-medium text-slate-900 truncate">
                            {conversation.other_user.full_name}
                          </p>
                          {conversation.unread_count > 0 && (
                            <Badge className="bg-indigo-600 text-white">
                              {conversation.unread_count}
                            </Badge>
                          )}
                        </div>
                        
                        <p className="text-xs text-slate-500">
                          @{conversation.other_user.username}
                          {conversation.other_user.is_creator && (
                            <Badge variant="secondary" className="ml-1">Creador</Badge>
                          )}
                        </p>
                        
                        {conversation.last_message && (
                          <p className="text-xs text-slate-400 truncate mt-1">
                            {conversation.last_message.message_type === 'text' 
                              ? conversation.last_message.content 
                              : `📎 ${conversation.last_message.message_type}`
                            }
                          </p>
                        )}
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Chat Area */}
        <Card className="lg:col-span-2">
          {selectedConversation ? (
            <>
              {/* Chat Header */}
              <CardHeader className="border-b">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <Avatar>
                      <AvatarImage src={selectedConversation.other_user.avatar_url} />
                      <AvatarFallback>
                        {selectedConversation.other_user.full_name.substring(0, 2).toUpperCase()}
                      </AvatarFallback>
                    </Avatar>
                    <div>
                      <h3 className="font-medium text-slate-900">
                        {selectedConversation.other_user.full_name}
                      </h3>
                      <p className="text-sm text-slate-500">
                        @{selectedConversation.other_user.username}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex items-center space-x-2">
                    <Badge variant="outline">
                      <Shield className="h-3 w-3 mr-1" />
                      Cifrado
                    </Badge>
                  </div>
                </div>
              </CardHeader>

              {/* Messages */}
              <CardContent className="p-4">
                <div className="h-[350px] overflow-y-auto space-y-4">
                  {loading ? (
                    <div className="flex justify-center items-center h-full">
                      <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex flex-col items-center justify-center h-full text-slate-500">
                      <MessageCircle className="h-12 w-12 mb-4 text-slate-300" />
                      <p>No hay mensajes aún</p>
                      <p className="text-sm">¡Envía el primer mensaje!</p>
                    </div>
                  ) : (
                    messages.map(renderMessage)
                  )}
                  <div ref={messagesEndRef} />
                </div>

                {/* Message Input */}
                <div className="border-t pt-4 mt-4">
                  <form onSubmit={sendMessage} className="space-y-3">
                    {/* Advanced options */}
                    <div className="flex flex-wrap gap-2">
                      <div className="flex items-center space-x-2">
                        <Switch
                          id="is_ppv"
                          checked={messageForm.is_ppv}
                          onCheckedChange={(checked) => setMessageForm({...messageForm, is_ppv: checked})}
                        />
                        <Label htmlFor="is_ppv" className="text-sm">PPV</Label>
                      </div>
                      
                      {messageForm.is_ppv && (
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Precio $"
                          value={messageForm.ppv_price}
                          onChange={(e) => setMessageForm({...messageForm, ppv_price: e.target.value})}
                          className="w-20 h-8"
                        />
                      )}

                      <div className="flex items-center space-x-2">
                        <Switch
                          id="is_tip"
                          checked={messageForm.is_tip}
                          onCheckedChange={(checked) => setMessageForm({...messageForm, is_tip: checked})}
                        />
                        <Label htmlFor="is_tip" className="text-sm">Propina</Label>
                      </div>
                      
                      {messageForm.is_tip && (
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="Cantidad $"
                          value={messageForm.tip_amount}
                          onChange={(e) => setMessageForm({...messageForm, tip_amount: e.target.value})}
                          className="w-24 h-8"
                        />
                      )}

                      <Select 
                        value={messageForm.auto_destruct_minutes?.toString() || ''} 
                        onValueChange={(value) => setMessageForm({...messageForm, auto_destruct_minutes: value ? parseInt(value) : null})}
                      >
                        <SelectTrigger className="w-32 h-8">
                          <SelectValue placeholder="Auto-destruir" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">Sin límite</SelectItem>
                          <SelectItem value="5">5 minutos</SelectItem>
                          <SelectItem value="30">30 minutos</SelectItem>
                          <SelectItem value="60">1 hora</SelectItem>
                          <SelectItem value="1440">24 horas</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    <div className="flex space-x-2">
                      <div className="flex-1">
                        <Input
                          value={newMessage}
                          onChange={(e) => setNewMessage(e.target.value)}
                          placeholder="Escribe tu mensaje..."
                          disabled={loading}
                        />
                      </div>
                      
                      <input
                        type="file"
                        id="file-upload"
                        accept="image/*,video/*,audio/*"
                        onChange={handleFileUpload}
                        className="hidden"
                      />
                      
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => document.getElementById('file-upload').click()}
                      >
                        📎
                      </Button>
                      
                      <Button type="submit" disabled={loading || (!newMessage.trim() && !messageForm.file)}>
                        <Send className="h-4 w-4" />
                      </Button>
                    </div>

                    {messageForm.file && (
                      <div className="text-sm text-slate-600">
                        Archivo seleccionado: {messageForm.file.name}
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          onClick={() => setMessageForm({...messageForm, file: null})}
                          className="ml-2"
                        >
                          ✕
                        </Button>
                      </div>
                    )}
                  </form>
                </div>
              </CardContent>
            </>
          ) : (
            <CardContent className="flex items-center justify-center h-full">
              <div className="text-center text-slate-500">
                <MessageCircle className="h-16 w-16 mx-auto mb-4 text-slate-300" />
                <h3 className="text-lg font-medium mb-2">Selecciona una conversación</h3>
                <p className="text-sm">Elige una conversación para empezar a chatear</p>
              </div>
            </CardContent>
          )}
        </Card>
      </div>
    </div>
  );
};

export default MessagingSystem;