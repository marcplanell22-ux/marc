import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Badge } from './components/ui/badge';
import { Progress } from './components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { toast } from './hooks/use-toast';
import { 
  Upload, 
  Save, 
  Camera, 
  Video as VideoIcon, 
  Link as LinkIcon,
  Plus,
  Trash2,
  User,
  Settings,
  Palette,
  Globe
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ProfileEditor = ({ user }) => {
  const [creator, setCreator] = useState(null);
  const [loading, setLoading] = useState(false);
  const [profileForm, setProfileForm] = useState({
    display_name: '',
    bio: '',
    category: '',
    tags: [],
    subscription_price: '',
    welcome_message: '',
    social_links: {},
    seo_title: '',
    seo_description: ''
  });
  const [bannerFile, setBannerFile] = useState(null);
  const [welcomeVideoFile, setWelcomeVideoFile] = useState(null);
  const [customSections, setCustomSections] = useState([]);

  const categories = [
    'fitness', 'cooking', 'art', 'music', 'lifestyle', 'gaming', 
    'education', 'comedy', 'fashion', 'travel', 'technology', 'beauty'
  ];

  const socialPlatforms = [
    'instagram', 'twitter', 'youtube', 'tiktok', 'facebook', 
    'linkedin', 'twitch', 'discord', 'onlyfans', 'website'
  ];

  useEffect(() => {
    if (user?.is_creator) {
      fetchCreatorProfile();
    }
  }, [user]);

  const fetchCreatorProfile = async () => {
    try {
      // First try to get the creator profile
      const response = await axios.get(`${API}/creators/${user.username}`);
      setCreator(response.data);
      
      setProfileForm({
        display_name: response.data.display_name || '',
        bio: response.data.bio || '',
        category: response.data.category || '',
        tags: response.data.tags || [],
        subscription_price: response.data.subscription_price?.toString() || '',
        welcome_message: response.data.welcome_message || '',
        social_links: response.data.social_links || {},
        seo_title: response.data.seo_title || '',
        seo_description: response.data.seo_description || ''
      });
      
      setCustomSections(response.data.custom_sections || []);
    } catch (error) {
      // If creator profile doesn't exist, we need to create one first
      if (error.response?.status === 404) {
        console.log('Creator profile not found, user needs to complete setup');
        setCreator({
          id: null,
          display_name: user.full_name,
          bio: '',
          category: '',
          tags: [],
          subscription_price: 9.99,
          profile_completion: 20
        });
        
        setProfileForm({
          display_name: user.full_name || '',
          bio: '',
          category: '',
          tags: [],
          subscription_price: '9.99',
          welcome_message: '',
          social_links: {},
          seo_title: '',
          seo_description: ''
        });
      } else {
        console.error('Error fetching creator profile:', error);
        toast({
          title: "Error",
          description: "No se pudo cargar el perfil del creador",
          variant: "destructive"
        });
      }
    }
  };

  const handleSaveProfile = async () => {
    try {
      setLoading(true);
      
      const updateData = {
        ...profileForm,
        tags: Array.isArray(profileForm.tags) ? profileForm.tags : profileForm.tags.split(',').map(tag => tag.trim()),
        subscription_price: parseFloat(profileForm.subscription_price),
        custom_sections: customSections
      };

      if (creator.id) {
        // Update existing profile
        await axios.put(`${API}/creators/${creator.id}`, updateData);
      } else {
        // Create new profile
        const response = await axios.post(`${API}/creators`, updateData);
        setCreator(prev => ({ ...prev, id: response.data.id }));
      }
      
      toast({
        title: "¡Perfil actualizado!",
        description: "Los cambios se han guardado exitosamente"
      });
      
      fetchCreatorProfile();
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al guardar el perfil",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleBannerUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.size > 5 * 1024 * 1024) {
      toast({
        title: "Error",
        description: "El archivo es muy grande (máximo 5MB)",
        variant: "destructive"
      });
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', file);

      await axios.post(`${API}/creators/${creator.id}/upload-banner`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast({
        title: "¡Banner actualizado!",
        description: "Tu imagen de portada se ha actualizado"
      });
      
      fetchCreatorProfile();
    } catch (error) {
      toast({
        title: "Error",
        description: "Error al subir la imagen",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleVideoUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    if (file.size > 50 * 1024 * 1024) {
      toast({
        title: "Error",
        description: "El video es muy grande (máximo 50MB)",
        variant: "destructive"
      });
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', file);

      await axios.post(`${API}/creators/${creator.id}/upload-welcome-video`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      toast({
        title: "¡Video de bienvenida actualizado!",
        description: "Tu video de bienvenida se ha subido exitosamente"
      });
      
      fetchCreatorProfile();
    } catch (error) {
      toast({
        title: "Error",
        description: "Error al subir el video",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const addCustomSection = () => {
    setCustomSections([
      ...customSections,
      {
        id: Date.now().toString(),
        title: '',
        content: '',
        type: 'text',
        visible: true
      }
    ]);
  };

  const updateCustomSection = (id, field, value) => {
    setCustomSections(sections =>
      sections.map(section =>
        section.id === id ? { ...section, [field]: value } : section
      )
    );
  };

  const removeCustomSection = (id) => {
    setCustomSections(sections => sections.filter(section => section.id !== id));
  };

  const addTag = (tag) => {
    if (tag && !profileForm.tags.includes(tag)) {
      setProfileForm({
        ...profileForm,
        tags: [...profileForm.tags, tag]
      });
    }
  };

  const removeTag = (tagToRemove) => {
    setProfileForm({
      ...profileForm,
      tags: profileForm.tags.filter(tag => tag !== tagToRemove)
    });
  };

  const addSocialLink = (platform, url) => {
    if (platform && url) {
      setProfileForm({
        ...profileForm,
        social_links: {
          ...profileForm.social_links,
          [platform]: url
        }
      });
    }
  };

  const removeSocialLink = (platform) => {
    const newLinks = { ...profileForm.social_links };
    delete newLinks[platform];
    setProfileForm({
      ...profileForm,
      social_links: newLinks
    });
  };

  if (!user?.is_creator) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <User className="h-12 w-12 text-slate-400 mx-auto mb-4" />
        <h1 className="text-2xl font-bold text-slate-900 mb-4">Acceso de Creador Requerido</h1>
        <p className="text-slate-600">Esta función está disponible solo para creadores.</p>
      </div>
    );
  }

  if (!creator) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="animate-pulse">
          <div className="h-8 bg-slate-200 rounded mb-4"></div>
          <div className="h-64 bg-slate-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Editar Perfil</h1>
        <p className="text-slate-600">Personaliza tu perfil para atraer más suscriptores</p>
        
        {creator.profile_completion < 100 && (
          <div className="mt-4 p-4 bg-yellow-50 rounded-lg border border-yellow-200">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-yellow-800">Completitud del perfil</span>
              <span className="text-sm text-yellow-700">{creator.profile_completion}%</span>
            </div>
            <Progress value={creator.profile_completion} className="h-2 mb-2" />
            <p className="text-xs text-yellow-700">
              Completa tu perfil para obtener más visibilidad y suscriptores
            </p>
          </div>
        )}
      </div>

      <Tabs defaultValue="basic" className="space-y-6">
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="basic">Información Básica</TabsTrigger>
          <TabsTrigger value="media">Multimedia</TabsTrigger>
          <TabsTrigger value="social">Redes Sociales</TabsTrigger>
          <TabsTrigger value="advanced">Avanzado</TabsTrigger>
        </TabsList>

        {/* Basic Information */}
        <TabsContent value="basic">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <User className="h-5 w-5 mr-2" />
                  Información Personal
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="display_name">Nombre de Creador *</Label>
                  <Input
                    id="display_name"
                    value={profileForm.display_name}
                    onChange={(e) => setProfileForm({...profileForm, display_name: e.target.value})}
                    placeholder="Tu nombre como creador"
                  />
                </div>

                <div>
                  <Label htmlFor="bio">Biografía *</Label>
                  <Textarea
                    id="bio"
                    value={profileForm.bio}
                    onChange={(e) => setProfileForm({...profileForm, bio: e.target.value})}
                    placeholder="Cuéntanos sobre ti y tu contenido..."
                    rows={4}
                  />
                </div>

                <div>
                  <Label htmlFor="category">Categoría *</Label>
                  <Select value={profileForm.category} onValueChange={(value) => setProfileForm({...profileForm, category: value})}>
                    <SelectTrigger>
                      <SelectValue placeholder="Selecciona una categoría" />
                    </SelectTrigger>
                    <SelectContent>
                      {categories.map(category => (
                        <SelectItem key={category} value={category}>
                          {category.charAt(0).toUpperCase() + category.slice(1)}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="subscription_price">Precio de Suscripción (USD) *</Label>
                  <Input
                    id="subscription_price"
                    type="number"
                    step="0.01"
                    value={profileForm.subscription_price}
                    onChange={(e) => setProfileForm({...profileForm, subscription_price: e.target.value})}
                    placeholder="9.99"
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Tags y Especialidades</CardTitle>
                <CardDescription>Ayuda a los fans a encontrarte</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <Label>Tags Actuales</Label>
                    <div className="flex flex-wrap gap-2 mt-2">
                      {profileForm.tags.map(tag => (
                        <Badge key={tag} variant="secondary" className="cursor-pointer" onClick={() => removeTag(tag)}>
                          {tag} ×
                        </Badge>
                      ))}
                    </div>
                  </div>
                  
                  <div>
                    <Label>Agregar Tag</Label>
                    <div className="flex gap-2">
                      <Input
                        placeholder="fitness, lifestyle, etc."
                        onKeyPress={(e) => {
                          if (e.key === 'Enter') {
                            e.preventDefault();
                            addTag(e.target.value);
                            e.target.value = '';
                          }
                        }}
                      />
                    </div>
                  </div>

                  <div>
                    <Label htmlFor="welcome_message">Mensaje de Bienvenida</Label>
                    <Textarea
                      id="welcome_message"
                      value={profileForm.welcome_message}
                      onChange={(e) => setProfileForm({...profileForm, welcome_message: e.target.value})}
                      placeholder="Mensaje automático para nuevos suscriptores..."
                      rows={3}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Multimedia */}
        <TabsContent value="media">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Camera className="h-5 w-5 mr-2" />
                  Imagen de Portada
                </CardTitle>
                <CardDescription>Imagen de banner (máximo 5MB)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {creator.banner_url && (
                    <div className="aspect-video bg-slate-100 rounded-lg overflow-hidden">
                      <img
                        src={creator.banner_url}
                        alt="Banner actual"
                        className="w-full h-full object-cover"
                      />
                    </div>
                  )}
                  
                  <div>
                    <input
                      type="file"
                      id="banner-upload"
                      accept="image/*"
                      onChange={handleBannerUpload}
                      className="hidden"
                    />
                    <Button
                      onClick={() => document.getElementById('banner-upload').click()}
                      disabled={loading}
                      className="w-full"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      {creator.banner_url ? 'Cambiar Banner' : 'Subir Banner'}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <VideoIcon className="h-5 w-5 mr-2" />
                  Video de Bienvenida
                </CardTitle>
                <CardDescription>Video de presentación (máximo 50MB)</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {creator.welcome_video_url && (
                    <div className="aspect-video bg-slate-100 rounded-lg overflow-hidden">
                      <video
                        src={creator.welcome_video_url}
                        controls
                        className="w-full h-full object-cover"
                      >
                        Tu navegador no soporta video.
                      </video>
                    </div>
                  )}
                  
                  <div>
                    <input
                      type="file"
                      id="video-upload"
                      accept="video/*"
                      onChange={handleVideoUpload}
                      className="hidden"
                    />
                    <Button
                      onClick={() => document.getElementById('video-upload').click()}
                      disabled={loading}
                      className="w-full"
                    >
                      <Upload className="h-4 w-4 mr-2" />
                      {creator.welcome_video_url ? 'Cambiar Video' : 'Subir Video'}
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Social Media */}
        <TabsContent value="social">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <LinkIcon className="h-5 w-5 mr-2" />
                Enlaces de Redes Sociales
              </CardTitle>
              <CardDescription>Conecta tus otras plataformas</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(profileForm.social_links).map(([platform, url]) => (
                  <div key={platform} className="flex gap-2">
                    <Input
                      value={url}
                      onChange={(e) => addSocialLink(platform, e.target.value)}
                      placeholder={`URL de ${platform}`}
                    />
                    <Button
                      variant="outline"
                      onClick={() => removeSocialLink(platform)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
                
                <div className="border-t pt-4">
                  <Label>Agregar Nueva Red Social</Label>
                  <div className="flex gap-2 mt-2">
                    <Select onValueChange={(platform) => {
                      if (!profileForm.social_links[platform]) {
                        addSocialLink(platform, '');
                      }
                    }}>
                      <SelectTrigger className="w-40">
                        <SelectValue placeholder="Plataforma" />
                      </SelectTrigger>
                      <SelectContent>
                        {socialPlatforms.map(platform => (
                          <SelectItem key={platform} value={platform}>
                            {platform.charAt(0).toUpperCase() + platform.slice(1)}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Advanced */}
        <TabsContent value="advanced">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Globe className="h-5 w-5 mr-2" />
                  SEO y Optimización
                </CardTitle>
                <CardDescription>Mejora la visibilidad de tu perfil</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <Label htmlFor="seo_title">Título SEO</Label>
                  <Input
                    id="seo_title"
                    value={profileForm.seo_title}
                    onChange={(e) => setProfileForm({...profileForm, seo_title: e.target.value})}
                    placeholder="Título optimizado para buscadores"
                  />
                </div>
                <div>
                  <Label htmlFor="seo_description">Descripción SEO</Label>
                  <Textarea
                    id="seo_description"
                    value={profileForm.seo_description}
                    onChange={(e) => setProfileForm({...profileForm, seo_description: e.target.value})}
                    placeholder="Descripción que aparecerá en buscadores..."
                    rows={3}
                  />
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <Palette className="h-5 w-5 mr-2" />
                  Secciones Personalizadas
                </CardTitle>
                <CardDescription>Crea secciones únicas para tu perfil</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {customSections.map((section, index) => (
                  <div key={section.id} className="border rounded-lg p-4">
                    <div className="flex justify-between items-center mb-3">
                      <h4 className="font-medium">Sección {index + 1}</h4>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => removeCustomSection(section.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    <div className="space-y-3">
                      <Input
                        placeholder="Título de la sección"
                        value={section.title}
                        onChange={(e) => updateCustomSection(section.id, 'title', e.target.value)}
                      />
                      <Textarea
                        placeholder="Contenido de la sección"
                        value={section.content}
                        onChange={(e) => updateCustomSection(section.id, 'content', e.target.value)}
                        rows={3}
                      />
                    </div>
                  </div>
                ))}
                
                <Button
                  variant="outline"
                  onClick={addCustomSection}
                  className="w-full"
                >
                  <Plus className="h-4 w-4 mr-2" />
                  Agregar Sección Personalizada
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Save Button */}
      <div className="mt-8 flex justify-end">
        <Button
          onClick={handleSaveProfile}
          disabled={loading}
          size="lg"
          className="bg-gradient-to-r from-indigo-600 to-purple-600 hover:from-indigo-700 hover:to-purple-700"
        >
          <Save className="h-4 w-4 mr-2" />
          {loading ? 'Guardando...' : 'Guardar Cambios'}
        </Button>
      </div>
    </div>
  );
};

export default ProfileEditor;