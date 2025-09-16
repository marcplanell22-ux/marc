import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Badge } from './components/ui/badge';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { Progress } from './components/ui/progress';
import { toast } from './hooks/use-toast';
import { 
  Heart, 
  MessageCircle, 
  Gift, 
  Share2, 
  Play, 
  Eye, 
  ThumbsUp, 
  Calendar,
  Star,
  Verified,
  Camera,
  Video,
  Music,
  FileText,
  ExternalLink,
  TrendingUp,
  Users,
  Award,
  Link as LinkIcon
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const CreatorProfile = ({ user }) => {
  const { username } = useParams();
  const [creator, setCreator] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('feed');
  const [isSubscribed, setIsSubscribed] = useState(false);

  useEffect(() => {
    if (username) {
      fetchCreatorProfile();
    }
  }, [username]);

  const fetchCreatorProfile = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/creators/${username}`);
      setCreator(response.data);
      
      // Check if current user is subscribed
      if (user) {
        checkSubscriptionStatus(response.data.id);
      }
    } catch (error) {
      console.error('Error fetching creator profile:', error);
      toast({
        title: "Error",
        description: "No se pudo cargar el perfil del creador",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const checkSubscriptionStatus = async (creatorId) => {
    try {
      // This would be implemented with a subscription check endpoint
      // For now, we'll assume not subscribed
      setIsSubscribed(false);
    } catch (error) {
      console.error('Error checking subscription:', error);
    }
  };

  const handleSubscribe = async () => {
    if (!user) {
      toast({
        title: "Inicia sesión",
        description: "Necesitas iniciar sesión para suscribirte",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await axios.post(`${API}/payments/subscribe`, {
        creator_id: creator.id,
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

  const handleMessage = async () => {
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
        recipient_id: creator.user_id
      });
      
      // Redirect to messages
      window.location.href = `/messages?conversation=${response.data.conversation_id}`;
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al crear conversación",
        variant: "destructive"
      });
    }
  };

  const handleTip = async () => {
    if (!user) {
      toast({
        title: "Inicia sesión",
        description: "Necesitas iniciar sesión para enviar propinas",
        variant: "destructive"
      });
      return;
    }

    try {
      const response = await axios.post(`${API}/payments/tip`, {
        creator_id: creator.id,
        amount: 5.0,
        message: "¡Gracias por tu contenido increíble!"
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

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  const getContentIcon = (type) => {
    switch (type) {
      case 'image': return <Camera className="h-4 w-4" />;
      case 'video': return <Video className="h-4 w-4" />;
      case 'audio': return <Music className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  const shareProfile = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Perfil de ${creator.display_name}`,
          text: creator.bio,
          url: window.location.href
        });
      } catch (error) {
        // Fallback to copying to clipboard
        copyToClipboard();
      }
    } else {
      copyToClipboard();
    }
  };

  const copyToClipboard = () => {
    navigator.clipboard.writeText(window.location.href);
    toast({
      title: "¡Enlace copiado!",
      description: "El enlace del perfil se copió al portapapeles"
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-50">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="animate-pulse">
            <div className="h-64 bg-slate-200 rounded-lg mb-6"></div>
            <div className="h-8 bg-slate-200 rounded mb-4"></div>
            <div className="h-4 bg-slate-200 rounded mb-6"></div>
            <div className="grid grid-cols-3 gap-4">
              <div className="h-32 bg-slate-200 rounded"></div>
              <div className="h-32 bg-slate-200 rounded"></div>
              <div className="h-32 bg-slate-200 rounded"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!creator) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">😔</div>
          <h1 className="text-2xl font-bold text-slate-900 mb-2">Creador no encontrado</h1>
          <p className="text-slate-600">El perfil que buscas no existe o no está disponible.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Hero Section with Banner */}
      <div className="relative">
        {/* Banner */}
        <div className="h-64 md:h-80 bg-gradient-to-br from-indigo-500 via-purple-600 to-pink-500 relative overflow-hidden">
          {creator.banner_url && (
            <img
              src={creator.banner_url}
              alt={`${creator.display_name} banner`}
              className="w-full h-full object-cover"
            />
          )}
          <div className="absolute inset-0 bg-black/20"></div>
        </div>

        {/* Profile Info Overlay */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="relative -mt-20 pb-8">
            <div className="bg-white rounded-xl shadow-xl p-6 md:p-8">
              <div className="flex flex-col md:flex-row md:items-start md:space-x-6">
                {/* Avatar */}
                <div className="flex-shrink-0 mx-auto md:mx-0 mb-4 md:mb-0">
                  <Avatar className="h-24 w-24 md:h-32 md:w-32 border-4 border-white shadow-lg">
                    <AvatarImage src={creator.user_info.avatar_url} />
                    <AvatarFallback className="text-xl md:text-2xl font-bold bg-gradient-to-br from-indigo-500 to-purple-600 text-white">
                      {creator.display_name.substring(0, 2).toUpperCase()}
                    </AvatarFallback>
                  </Avatar>
                </div>

                {/* Creator Info */}
                <div className="flex-1 text-center md:text-left">
                  <div className="flex flex-col md:flex-row md:items-center md:justify-between mb-4">
                    <div>
                      <h1 className="text-2xl md:text-3xl font-bold text-slate-900 mb-2 flex items-center justify-center md:justify-start">
                        {creator.display_name}
                        {creator.is_verified && (
                          <Verified className="h-6 w-6 text-blue-500 ml-2" />
                        )}
                      </h1>
                      <p className="text-slate-600 mb-2">@{creator.user_info.username}</p>
                      <div className="flex items-center justify-center md:justify-start space-x-2">
                        <Badge variant="secondary">{creator.category}</Badge>
                        <Badge variant="outline">
                          <Star className="h-3 w-3 mr-1" />
                          {creator.rating.toFixed(1)}
                        </Badge>
                      </div>
                    </div>

                    {/* Action Buttons */}
                    <div className="flex flex-col sm:flex-row gap-2 mt-4 md:mt-0">
                      <Button
                        onClick={handleSubscribe}
                        className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
                        disabled={isSubscribed}
                      >
                        <Heart className="h-4 w-4 mr-2" />
                        {isSubscribed ? 'Suscrito' : `Suscribirse $${creator.subscription_price}/mes`}
                      </Button>
                      
                      <div className="flex gap-2">
                        <Button variant="outline" onClick={handleMessage}>
                          <MessageCircle className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" onClick={handleTip}>
                          <Gift className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" onClick={shareProfile}>
                          <Share2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>

                  {/* Bio */}
                  <p className="text-slate-700 mb-4 max-w-2xl">{creator.bio}</p>

                  {/* Stats */}
                  <div className="grid grid-cols-3 md:grid-cols-5 gap-4 text-center">
                    <div>
                      <div className="text-xl md:text-2xl font-bold text-slate-900">{creator.content_count}</div>
                      <div className="text-xs md:text-sm text-slate-600">Publicaciones</div>
                    </div>
                    <div>
                      <div className="text-xl md:text-2xl font-bold text-slate-900">{creator.follower_count}</div>
                      <div className="text-xs md:text-sm text-slate-600">Suscriptores</div>
                    </div>
                    <div>
                      <div className="text-xl md:text-2xl font-bold text-slate-900">{creator.total_likes}</div>
                      <div className="text-xs md:text-sm text-slate-600">Likes</div>
                    </div>
                    <div className="hidden md:block">
                      <div className="text-xl md:text-2xl font-bold text-green-600">{creator.recent_activity.posts_this_month}</div>
                      <div className="text-xs md:text-sm text-slate-600">Este mes</div>
                    </div>
                    <div className="hidden md:block">
                      <div className="text-xl md:text-2xl font-bold text-indigo-600">{creator.profile_completion}%</div>
                      <div className="text-xs md:text-sm text-slate-600">Perfil completo</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Content Sections */}
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pb-12">
        {/* Welcome Video */}
        {creator.welcome_video_url && (
          <Card className="mb-8">
            <CardHeader>
              <CardTitle className="flex items-center">
                <Play className="h-5 w-5 mr-2 text-indigo-600" />
                Video de Bienvenida
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="aspect-video bg-slate-100 rounded-lg overflow-hidden">
                <video
                  src={creator.welcome_video_url}
                  controls
                  className="w-full h-full object-cover"
                  poster={creator.banner_url}
                >
                  Tu navegador no soporta la reproducción de video.
                </video>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Statistics Section */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-8">
          {/* Content Statistics */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <TrendingUp className="h-5 w-5 mr-2 text-green-600" />
                Contenido por Tipo
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {Object.entries(creator.content_stats || {}).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between">
                    <div className="flex items-center">
                      {getContentIcon(type)}
                      <span className="ml-2 capitalize">{type}</span>
                    </div>
                    <Badge variant="secondary">{count}</Badge>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center">
                <Calendar className="h-5 w-5 mr-2 text-blue-600" />
                Actividad Reciente
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Posts este mes</span>
                  <span className="font-semibold">{creator.recent_activity.posts_this_month}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Frecuencia</span>
                  <Badge variant={creator.recent_activity.posting_frequency === 'Regular' ? 'default' : 'secondary'}>
                    {creator.recent_activity.posting_frequency}
                  </Badge>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-sm text-slate-600">Miembro desde</span>
                  <span className="text-sm font-medium">{formatDate(creator.created_at)}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Social Links */}
          {creator.social_links && Object.keys(creator.social_links).length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg flex items-center">
                  <LinkIcon className="h-5 w-5 mr-2 text-purple-600" />
                  Redes Sociales
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(creator.social_links).map(([platform, url]) => (
                    <a
                      key={platform}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center text-sm text-indigo-600 hover:text-indigo-800 transition-colors"
                    >
                      <ExternalLink className="h-4 w-4 mr-2" />
                      <span className="capitalize">{platform}</span>
                    </a>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Content Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="feed">Feed Público</TabsTrigger>
            <TabsTrigger value="premium">Contenido Premium</TabsTrigger>
            <TabsTrigger value="about">Acerca de</TabsTrigger>
          </TabsList>

          {/* Public Feed */}
          <TabsContent value="feed" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {creator.public_content && creator.public_content.length > 0 ? (
                creator.public_content.map((content) => (
                  <Card key={content.id} className="overflow-hidden hover:shadow-lg transition-shadow">
                    <div className="aspect-square bg-slate-100 relative">
                      {content.file_path ? (
                        <img
                          src={`${API}/content/${content.id}/file`}
                          alt={content.title}
                          className="w-full h-full object-cover"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
                          {getContentIcon(content.content_type)}
                        </div>
                      )}
                      <div className="absolute top-2 right-2">
                        <Badge variant="secondary" className="bg-white/90">
                          {getContentIcon(content.content_type)}
                        </Badge>
                      </div>
                    </div>
                    <CardContent className="p-4">
                      <h3 className="font-semibold text-slate-900 mb-2">{content.title}</h3>
                      <p className="text-sm text-slate-600 mb-3 line-clamp-2">{content.description}</p>
                      <div className="flex items-center justify-between text-xs text-slate-500">
                        <span className="flex items-center">
                          <ThumbsUp className="h-3 w-3 mr-1" />
                          {content.likes}
                        </span>
                        <span className="flex items-center">
                          <Eye className="h-3 w-3 mr-1" />
                          {content.views}
                        </span>
                        <span>{formatDate(content.created_at)}</span>
                      </div>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="col-span-2 text-center py-12">
                  <FileText className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 mb-2">Sin contenido público</h3>
                  <p className="text-slate-600">Este creador aún no ha compartido contenido público.</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* Premium Previews */}
          <TabsContent value="premium" className="mt-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {creator.premium_previews && creator.premium_previews.length > 0 ? (
                creator.premium_previews.map((content) => (
                  <Card key={content.id} className="overflow-hidden relative">
                    <div className="aspect-square bg-slate-100 relative">
                      {content.file_path ? (
                        <div className="relative">
                          <img
                            src={`${API}/content/${content.id}/file`}
                            alt={content.title}
                            className="w-full h-full object-cover blur-sm"
                          />
                          <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                            <div className="text-center text-white">
                              <Eye className="h-8 w-8 mx-auto mb-2" />
                              <p className="text-sm font-medium">Vista Previa</p>
                            </div>
                          </div>
                        </div>
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200">
                          {getContentIcon(content.content_type)}
                        </div>
                      )}
                      
                      {/* Watermark */}
                      <div className="absolute inset-0 pointer-events-none">
                        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 text-white font-bold text-2xl opacity-20 rotate-45">
                          PREVIEW
                        </div>
                      </div>
                    </div>
                    
                    <CardContent className="p-4">
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="font-semibold text-slate-900">{content.title}</h3>
                        <Badge className="bg-gradient-to-r from-yellow-500 to-orange-500 text-white">
                          {content.is_premium ? 'Premium' : `$${content.ppv_price}`}
                        </Badge>
                      </div>
                      <p className="text-sm text-slate-600 mb-3 line-clamp-2">{content.description}</p>
                      <Button 
                        className="w-full" 
                        onClick={handleSubscribe}
                        disabled={isSubscribed}
                      >
                        {content.is_premium ? 'Suscribirse para ver' : `Pagar $${content.ppv_price}`}
                      </Button>
                    </CardContent>
                  </Card>
                ))
              ) : (
                <div className="col-span-2 text-center py-12">
                  <Award className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                  <h3 className="text-lg font-medium text-slate-900 mb-2">Sin contenido premium</h3>
                  <p className="text-slate-600">Este creador aún no ha compartido contenido premium.</p>
                </div>
              )}
            </div>
          </TabsContent>

          {/* About */}
          <TabsContent value="about" className="mt-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Acerca del Creador</CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <h4 className="font-medium text-slate-900 mb-2">Biografía</h4>
                    <p className="text-slate-700">{creator.bio}</p>
                  </div>
                  
                  <div>
                    <h4 className="font-medium text-slate-900 mb-2">Categoría</h4>
                    <Badge>{creator.category}</Badge>
                  </div>
                  
                  {creator.tags && creator.tags.length > 0 && (
                    <div>
                      <h4 className="font-medium text-slate-900 mb-2">Etiquetas</h4>
                      <div className="flex flex-wrap gap-2">
                        {creator.tags.map(tag => (
                          <Badge key={tag} variant="secondary">{tag}</Badge>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {creator.welcome_message && (
                    <div>
                      <h4 className="font-medium text-slate-900 mb-2">Mensaje de Bienvenida</h4>
                      <p className="text-slate-700 bg-slate-50 p-3 rounded-lg">
                        {creator.welcome_message}
                      </p>
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Estadísticas del Perfil</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-sm font-medium text-slate-700">Completitud del Perfil</span>
                        <span className="text-sm text-slate-600">{creator.profile_completion}%</span>
                      </div>
                      <Progress value={creator.profile_completion} className="h-2" />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-4 pt-4">
                      <div className="text-center">
                        <div className="text-2xl font-bold text-indigo-600">{creator.content_count}</div>
                        <div className="text-xs text-slate-600">Total Posts</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">{creator.total_likes}</div>
                        <div className="text-xs text-slate-600">Total Likes</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-purple-600">{creator.follower_count}</div>
                        <div className="text-xs text-slate-600">Seguidores</div>
                      </div>
                      <div className="text-center">
                        <div className="text-2xl font-bold text-yellow-600">{creator.rating.toFixed(1)}</div>
                        <div className="text-xs text-slate-600">Rating</div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
};

export default CreatorProfile;