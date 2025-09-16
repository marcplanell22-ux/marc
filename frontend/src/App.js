import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';
import Dashboard from './Dashboard';
import ContentScheduler from './ContentScheduler';
import MessagingSystem from './MessagingSystem';
import CreatorProfile from './CreatorProfile';
import ProfileEditor from './ProfileEditor';

// Import Shadcn components
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Badge } from './components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Switch } from './components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { toast } from './hooks/use-toast';
import { Toaster } from './components/ui/toaster';

// Icons
import { Search, Heart, Play, DollarSign, Users, TrendingUp, Star, Camera, Video, Image, Music, Plus, LogOut, Settings, Menu, X, Gift, MessageCircle } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = React.createContext();

const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    const response = await axios.post(`${API}/auth/login`, { email, password });
    const { access_token, user: userData } = response.data;
    
    localStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setUser(userData);
    
    return userData;
  };

  const register = async (userData) => {
    const response = await axios.post(`${API}/auth/register`, userData);
    const { access_token, user: newUser } = response.data;
    
    localStorage.setItem('token', access_token);
    axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
    setUser(newUser);
    
    return newUser;
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

// Header Component
const Header = () => {
  const { user, logout } = useAuth();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          {/* Logo */}
          <div className="flex items-center space-x-4">
            <div className="text-2xl font-bold bg-gradient-to-r from-orange-500 via-red-500 to-yellow-500 bg-clip-text text-transparent">
              CreatorHub
            </div>
          </div>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <a href="/" className="text-slate-600 hover:text-slate-900 transition-colors">Inicio</a>
            <a href="/explore" className="text-slate-600 hover:text-slate-900 transition-colors">Explorar</a>
            {user && (
              <a href="/messages" className="text-slate-600 hover:text-slate-900 transition-colors">Mensajes</a>
            )}
            {user?.is_creator && (
              <>
                <a href="/dashboard" className="text-slate-600 hover:text-slate-900 transition-colors">Dashboard</a>
                <a href="/schedule" className="text-slate-600 hover:text-slate-900 transition-colors">Programar</a>
                <a href="/profile/edit" className="text-slate-600 hover:text-slate-900 transition-colors">Mi Perfil</a>
              </>
            )}
          </nav>

          {/* User Menu */}
          <div className="hidden md:flex items-center space-x-4">
            {user ? (
              <div className="flex items-center space-x-3">
                <Avatar>
                  <AvatarImage src={user.avatar_url} />
                  <AvatarFallback>{user.full_name.substring(0, 2).toUpperCase()}</AvatarFallback>
                </Avatar>
                <Button variant="ghost" onClick={logout}>
                  <LogOut className="h-4 w-4" />
                </Button>
              </div>
            ) : (
              <div className="space-x-2">
                <Button variant="ghost">Iniciar Sesión</Button>
                <Button>Registrarse</Button>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <Button
            variant="ghost"
            className="md:hidden"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>

        {/* Mobile Menu */}
        {mobileMenuOpen && (
          <div className="md:hidden border-t border-slate-200 py-4">
            <nav className="space-y-2">
              <a href="/" className="block px-4 py-2 text-slate-600 hover:text-slate-900">Inicio</a>
              <a href="/explore" className="block px-4 py-2 text-slate-600 hover:text-slate-900">Explorar</a>
              {user && (
                <a href="/messages" className="block px-4 py-2 text-slate-600 hover:text-slate-900">Mensajes</a>
              )}
              {user?.is_creator && (
                <>
                  <a href="/dashboard" className="block px-4 py-2 text-slate-600 hover:text-slate-900">Dashboard</a>
                  <a href="/schedule" className="block px-4 py-2 text-slate-600 hover:text-slate-900">Programar</a>
                  <a href="/profile/edit" className="block px-4 py-2 text-slate-600 hover:text-slate-900">Mi Perfil</a>
                </>
              )}
            </nav>
            
            {user ? (
              <div className="mt-4 pt-4 border-t border-slate-200">
                <div className="flex items-center px-4 py-2">
                  <Avatar className="h-8 w-8 mr-3">
                    <AvatarImage src={user.avatar_url} />
                    <AvatarFallback>{user.full_name.substring(0, 2).toUpperCase()}</AvatarFallback>
                  </Avatar>
                  <span className="text-sm font-medium">{user.full_name}</span>
                </div>
                <Button variant="ghost" className="w-full justify-start px-4" onClick={logout}>
                  <LogOut className="h-4 w-4 mr-2" />
                  Cerrar Sesión
                </Button>
              </div>
            ) : (
              <div className="mt-4 pt-4 border-t border-slate-200 space-y-2 px-4">
                <Button variant="ghost" className="w-full">Iniciar Sesión</Button>
                <Button className="w-full">Registrarse</Button>
              </div>
            )}
          </div>
        )}
      </div>
    </header>
  );
};

// Landing Page Component
const LandingPage = () => {
  const { user } = useAuth();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-slate-50 via-white to-indigo-50 pt-20 pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-5xl md:text-7xl font-bold text-slate-900 mb-8 leading-tight">
              {user ? (
                <>
                  Monetiza Tu
                  <span className="bg-gradient-to-r from-orange-500 via-red-500 to-yellow-500 bg-clip-text text-transparent"> Pasión</span>
                </>
              ) : (
                <>
                  Conecta con tus
                  <span className="bg-gradient-to-r from-orange-500 via-red-500 to-yellow-500 bg-clip-text text-transparent"> Fans</span>
                </>
              )}
            </h1>
            <p className="text-xl md:text-2xl text-slate-600 mb-12 max-w-3xl mx-auto leading-relaxed">
              {user 
                ? `Descubre contenido exclusivo premium, conecta con tus creadores favoritos y disfruta de la mejor experiencia de suscripción sin límites.`
                : `La plataforma definitiva para creadores de contenido. Monetiza tu pasión con comisiones competitivas al 9.9%, 
                  pagos rápidos en 24h y herramientas avanzadas de analítica.`
              }
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-16">
              {user ? (
                <>
                  <Button size="lg" className="text-lg px-8 py-4 bg-gradient-to-r from-orange-500 via-red-500 to-yellow-500 hover:from-orange-600 hover:via-red-600 hover:to-yellow-600" onClick={() => window.location.href = '/explore'}>
                    🎯 Descubrir Creadores
                  </Button>
                  {user.is_creator && (
                    <Button variant="outline" size="lg" className="text-lg px-8 py-4" onClick={() => window.location.href = '/dashboard'}>
                      📊 Mi Dashboard
                    </Button>
                  )}
                  <Button variant="outline" size="lg" className="text-lg px-8 py-4" onClick={() => window.location.href = '/messages'}>
                    💬 Mis Conversaciones
                  </Button>
                </>
              ) : (
                <>
                  <AuthModal mode="register" />
                  <Button variant="outline" size="lg" className="text-lg px-8 py-4">
                    🎬 Ver Demo en Vivo
                  </Button>
                </>
              )}
            </div>

            {/* Stats */}
            <div className="grid grid-cols-3 gap-8 max-w-2xl mx-auto">
              <div className="text-center">
                <div className="text-3xl font-bold text-slate-900">9.9%</div>
                <div className="text-sm text-slate-600">Comisión Competitiva</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-slate-900">24h</div>
                <div className="text-sm text-slate-600">Pagos Rápidos</div>
              </div>
              <div className="text-center">
                <div className="text-3xl font-bold text-slate-900">50k+</div>
                <div className="text-sm text-slate-600">Creadores Activos</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-24 bg-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-slate-900 mb-4">Todo lo que necesitas</h2>
            <p className="text-xl text-slate-600">Herramientas poderosas para hacer crecer tu negocio</p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <CardHeader>
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center mb-4">
                  <DollarSign className="h-6 w-6 text-indigo-600" />
                </div>
                <CardTitle>Monetización Flexible</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600">Suscripciones, PPV, propinas y bundles. Múltiples formas de generar ingresos.</p>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <CardHeader>
                <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mb-4">
                  <TrendingUp className="h-6 w-6 text-purple-600" />
                </div>
                <CardTitle>Analíticas Avanzadas</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600">Insights detallados sobre tus fans, ingresos y performance de contenido.</p>
              </CardContent>
            </Card>

            <Card className="border-0 shadow-lg hover:shadow-xl transition-shadow duration-300">
              <CardHeader>
                <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mb-4">
                  <Users className="h-6 w-6 text-green-600" />
                </div>
                <CardTitle>Descubrimiento Inteligente</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-slate-600">Algoritmo avanzado que conecta a los fans con el contenido perfecto.</p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>
    </div>
  );
};

// Auth Modal Component
const AuthModal = ({ mode = 'login' }) => {
  const [isLogin, setIsLogin] = useState(mode === 'login');
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    username: '',
    full_name: '',
    is_creator: false
  });
  const [loading, setLoading] = useState(false);
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (isLogin) {
        await login(formData.email, formData.password);
        toast({ title: "¡Bienvenido de vuelta!" });
      } else {
        await register(formData);
        toast({ title: "¡Cuenta creada exitosamente!" });
      }
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Algo salió mal",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="lg" className="text-lg px-8 py-4 bg-gradient-to-r from-orange-500 via-red-500 to-yellow-500 hover:from-orange-600 hover:via-red-600 hover:to-yellow-600 shadow-lg transform hover:scale-105 transition-all duration-200">
          {mode === 'login' ? '🚀 Iniciar Sesión' : '🔥 Empezar Gratis Ahora'}
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md max-w-lg mx-auto p-6 bg-white rounded-lg shadow-xl border-0">
        <DialogHeader className="mb-6">
          <DialogTitle className="text-xl font-semibold text-slate-900 mb-2">
            {isLogin ? 'Iniciar Sesión' : 'Crear Cuenta'}
          </DialogTitle>
          <DialogDescription className="text-slate-600">
            {isLogin ? '¡Bienvenido de vuelta!' : 'Únete a miles de creadores exitosos'}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-5">
          {!isLogin && (
            <>
              <div className="space-y-2">
                <Label htmlFor="full_name" className="text-sm font-medium text-slate-700">
                  Nombre Completo
                </Label>
                <Input
                  id="full_name"
                  type="text"
                  placeholder="Tu nombre completo"
                  className="w-full h-10 px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  value={formData.full_name}
                  onChange={(e) => setFormData({ ...formData, full_name: e.target.value })}
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="username" className="text-sm font-medium text-slate-700">
                  Nombre de Usuario
                </Label>
                <Input
                  id="username"
                  type="text"
                  placeholder="@tunombredeusuario"
                  className="w-full h-10 px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  value={formData.username}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  required
                />
              </div>
              
              <div className="flex items-center space-x-3 p-3 bg-slate-50 rounded-md">
                <Switch
                  id="is_creator"
                  checked={formData.is_creator}
                  onCheckedChange={(checked) => setFormData({ ...formData, is_creator: checked })}
                />
                <Label htmlFor="is_creator" className="text-sm font-medium text-slate-700 cursor-pointer">
                  Soy un creador de contenido
                </Label>
              </div>
            </>
          )}
          
          <div className="space-y-2">
            <Label htmlFor="email" className="text-sm font-medium text-slate-700">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              placeholder="tu@email.com"
              className="w-full h-10 px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              required
            />
          </div>
          
          <div className="space-y-2">
            <Label htmlFor="password" className="text-sm font-medium text-slate-700">
              Contraseña
            </Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              className="w-full h-10 px-3 py-2 border border-slate-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              value={formData.password}
              onChange={(e) => setFormData({ ...formData, password: e.target.value })}
              required
            />
          </div>

          <Button 
            type="submit" 
            className="w-full h-11 bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700 text-white font-medium rounded-md transition-all duration-200" 
            disabled={loading}
          >
            {loading ? 'Procesando...' : (isLogin ? 'Iniciar Sesión' : 'Crear Cuenta')}
          </Button>
        </form>

        <div className="text-center mt-6 pt-4 border-t border-slate-200">
          <button
            type="button"
            className="text-sm text-indigo-600 hover:text-indigo-500 font-medium transition-colors"
            onClick={() => setIsLogin(!isLogin)}
          >
            {isLogin ? '¿No tienes cuenta? Regístrate' : '¿Ya tienes cuenta? Inicia sesión'}
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
};

// Explore Page Component
const ExplorePage = () => {
  const [creators, setCreators] = useState([]);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [loading, setLoading] = useState(true);
  const { user } = useAuth();

  const categories = [
    { value: 'all', label: 'Todos' },
    { value: 'fitness', label: 'Fitness' },
    { value: 'cooking', label: 'Cocina' },
    { value: 'art', label: 'Arte' },
    { value: 'music', label: 'Música' },
    { value: 'lifestyle', label: 'Lifestyle' },
    { value: 'gaming', label: 'Gaming' }
  ];

  useEffect(() => {
    fetchCreators();
  }, [selectedCategory, searchTerm]);

  const fetchCreators = async () => {
    try {
      const params = new URLSearchParams();
      if (selectedCategory !== 'all') params.append('category', selectedCategory);
      if (searchTerm) params.append('search', searchTerm);

      const response = await axios.get(`${API}/creators?${params}`);
      setCreators(response.data);
    } catch (error) {
      console.error('Error fetching creators:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSubscribe = async (creatorId) => {
    try {
      const response = await axios.post(`${API}/payments/subscribe`, {
        creator_id: creatorId,
        plan_type: 'premium'
      });
      
      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al procesar la suscripción",
        variant: "destructive"
      });
    }
  };

  const handleTip = async (creatorId) => {
    try {
      const response = await axios.post(`${API}/payments/tip`, {
        creator_id: creatorId,
        amount: 5.0,
        message: "¡Gracias por tu contenido!"
      });
      
      // Redirect to Stripe checkout
      window.location.href = response.data.checkout_url;
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al procesar la propina",
        variant: "destructive"
      });
    }
  };

  const handleMessage = async (creatorUserId) => {
    if (!user) {
      toast({
        title: "Inicia sesión",
        description: "Necesitas iniciar sesión para enviar mensajes",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await axios.post(`${API}/conversations`, {
        recipient_id: creatorUserId
      });
      
      // Redirect to messages with the conversation
      window.location.href = `/messages?conversation=${response.data.conversation_id}`;
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al crear conversación",
        variant: "destructive"
      });
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-4">Descubre Creadores Increíbles</h1>
        <p className="text-slate-600 mb-6">Encuentra contenido exclusivo de tus creadores favoritos y descubre nuevos talentos</p>
        
        {/* Search and Filters */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 h-4 w-4" />
            <Input
              placeholder="Buscar creadores por nombre, descripción o tags..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <Select value={selectedCategory} onValueChange={setSelectedCategory}>
            <SelectTrigger className="w-48">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {categories.map(category => (
                <SelectItem key={category.value} value={category.value}>
                  {category.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        {/* Category Stats */}
        <div className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-white rounded-lg border">
            <div className="text-2xl font-bold text-indigo-600">{creators.length}</div>
            <div className="text-sm text-slate-600">Creadores Activos</div>
          </div>
          <div className="text-center p-3 bg-white rounded-lg border">
            <div className="text-2xl font-bold text-green-600">50+</div>
            <div className="text-sm text-slate-600">Categorías</div>
          </div>
          <div className="text-center p-3 bg-white rounded-lg border">
            <div className="text-2xl font-bold text-purple-600">1000+</div>
            <div className="text-sm text-slate-600">Contenidos</div>
          </div>
          <div className="text-center p-3 bg-white rounded-lg border">
            <div className="text-2xl font-bold text-yellow-600">9.9%</div>
            <div className="text-sm text-slate-600">Comisión</div>
          </div>
        </div>
      </div>

      {/* Creators Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {[...Array(6)].map((_, i) => (
            <Card key={i} className="animate-pulse">
              <div className="h-48 bg-slate-200 rounded-t-lg"></div>
              <CardContent className="p-4">
                <div className="h-4 bg-slate-200 rounded mb-2"></div>
                <div className="h-3 bg-slate-200 rounded mb-4"></div>
                <div className="flex gap-2">
                  <div className="h-8 bg-slate-200 rounded flex-1"></div>
                  <div className="h-8 bg-slate-200 rounded w-16"></div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      ) : creators.length === 0 ? (
        <div className="text-center py-12">
          <Camera className="h-16 w-16 text-slate-400 mx-auto mb-6" />
          <h3 className="text-xl font-medium text-slate-900 mb-2">
            {searchTerm || selectedCategory !== 'all' 
              ? 'No se encontraron creadores' 
              : 'Sé el primer creador'
            }
          </h3>
          <p className="text-slate-600 mb-6">
            {searchTerm || selectedCategory !== 'all'
              ? 'Intenta con otros términos de búsqueda o categorías diferentes.'
              : 'Únete como creador y empieza a monetizar tu contenido.'
            }
          </p>
          {!user ? (
            <AuthModal mode="register" />
          ) : !user.is_creator ? (
            <Button onClick={() => window.location.href = '/profile/edit'}>
              Convertirse en Creador
            </Button>
          ) : null}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {creators.map(creator => (
            <Card key={creator.id} className="overflow-hidden hover:shadow-xl transition-shadow duration-300 cursor-pointer group">
              <div 
                className="relative h-48 bg-gradient-to-br from-orange-500 via-red-500 to-yellow-500"
                onClick={() => window.location.href = `/creator/${creator.user_info?.username || creator.id}`}
              >
                {creator.banner_url ? (
                  <img src={creator.banner_url} alt={creator.display_name} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center">
                    <Camera className="h-12 w-12 text-white/50" />
                  </div>
                )}
                
                {/* Creator Avatar */}
                <div className="absolute -bottom-6 left-4">
                  <Avatar className="h-12 w-12 border-4 border-white">
                    <AvatarFallback className="bg-white text-slate-900">
                      {creator.display_name.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </div>
                
                {creator.is_verified && (
                  <div className="absolute top-4 right-4">
                    <Badge className="bg-blue-500 text-white">
                      <Star className="h-3 w-3 mr-1" />
                      Verificado
                    </Badge>
                  </div>
                )}
              </div>

              <CardContent className="pt-8 p-6">
                <div className="mb-4" onClick={() => window.location.href = `/creator/${creator.user_info?.username || creator.id}`}>
                  <h3 className="font-bold text-lg text-slate-900 mb-1 group-hover:text-indigo-600 transition-colors">{creator.display_name}</h3>
                  <p className="text-slate-600 text-sm line-clamp-2">{creator.bio}</p>
                </div>

                <div className="flex items-center justify-between text-sm text-slate-500 mb-4">
                  <span className="flex items-center">
                    <Users className="h-4 w-4 mr-1" />
                    {creator.follower_count} fans
                  </span>
                  <span className="flex items-center">
                    <Play className="h-4 w-4 mr-1" />
                    {creator.content_count} contenidos
                  </span>
                </div>

                <div className="flex gap-2">
                  <Button 
                    className="flex-1 bg-gradient-to-r from-orange-500 via-red-500 to-yellow-500 hover:from-orange-600 hover:via-red-600 hover:to-yellow-600"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleSubscribe(creator.id);
                    }}
                  >
                    <Heart className="h-4 w-4 mr-1" />
                    Suscribirse
                  </Button>
                  {user && (
                    <Button 
                      variant="outline" 
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleMessage(creator.user_id);
                      }}
                    >
                      <MessageCircle className="h-4 w-4" />
                    </Button>
                  )}
                  <Button 
                    variant="outline" 
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      handleTip(creator.id);
                    }}
                  >
                    <Gift className="h-4 w-4" />
                  </Button>
                </div>

                <div className="mt-3 flex flex-wrap gap-1">
                  {creator.tags.slice(0, 3).map(tag => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {!loading && creators.length === 0 && (
        <div className="text-center py-12">
          <Camera className="h-12 w-12 text-slate-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-slate-900 mb-2">No se encontraron creadores</h3>
          <p className="text-slate-600">Intenta con otros términos de búsqueda o categorías.</p>
        </div>
      )}
    </div>
  );
};

// Main App Component
function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-slate-50">
          <Header />
          <main>
            <AppRoutes />
          </main>
          <Toaster />
        </div>
      </BrowserRouter>
    </AuthProvider>
  );
}

// Routes Component
function AppRoutes() {
  const { user } = useAuth();

  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/explore" element={<ExplorePage />} />
      <Route path="/dashboard" element={<Dashboard user={user} />} />
      <Route path="/schedule" element={<ContentScheduler user={user} />} />
      <Route path="/messages" element={<MessagingSystem user={user} />} />
      <Route path="/creator/:username" element={<CreatorProfile user={user} />} />
      <Route path="/profile/edit" element={<ProfileEditor user={user} />} />
      <Route path="/subscription-success" element={
        <div className="max-w-2xl mx-auto py-16 px-4 text-center">
          <div className="bg-green-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6">
            <Heart className="h-8 w-8 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mb-4">¡Suscripción Exitosa!</h1>
          <p className="text-slate-600 mb-8">Ya puedes acceder a todo el contenido exclusivo.</p>
          <Button onClick={() => window.location.href = '/explore'}>Continuar Explorando</Button>
        </div>
      } />
      <Route path="/tip-success" element={
        <div className="max-w-2xl mx-auto py-16 px-4 text-center">
          <div className="bg-yellow-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6">
            <Gift className="h-8 w-8 text-yellow-600" />
          </div>
          <h1 className="text-2xl font-bold text-slate-900 mb-4">¡Propina Enviada!</h1>
          <p className="text-slate-600 mb-8">El creador ha recibido tu apoyo. ¡Gracias por contribuir!</p>
          <Button onClick={() => window.location.href = '/explore'}>Continuar Explorando</Button>
        </div>
      } />
    </Routes>
  );
}

export default App;