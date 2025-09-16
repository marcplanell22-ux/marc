import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from './components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from './components/ui/tabs';
import { Button } from './components/ui/button';
import { Input } from './components/ui/input';
import { Label } from './components/ui/label';
import { Textarea } from './components/ui/textarea';
import { Switch } from './components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './components/ui/select';
import { Calendar } from './components/ui/calendar';
import { Badge } from './components/ui/badge';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from './components/ui/dialog';
import { toast } from './hooks/use-toast';
import { 
  Calendar as CalendarIcon, 
  Clock, 
  Plus, 
  Edit3, 
  Trash2, 
  Repeat, 
  Save,
  Eye,
  X
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ContentScheduler = ({ user }) => {
  const [scheduledContent, setScheduledContent] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [loading, setLoading] = useState(false);
  const [showScheduleModal, setShowScheduleModal] = useState(false);
  const [editingContent, setEditingContent] = useState(null);

  const [scheduleForm, setScheduleForm] = useState({
    title: '',
    description: '',
    scheduled_date: '',
    scheduled_time: '',
    is_premium: false,
    is_ppv: false,
    ppv_price: '',
    tags: '',
    file: null,
    is_recurring: false,
    recurrence_type: '',
    recurrence_end_date: ''
  });

  const [templateForm, setTemplateForm] = useState({
    name: '',
    title_template: '',
    description_template: '',
    tags: '',
    is_premium: false,
    is_ppv: false,
    ppv_price: ''
  });

  useEffect(() => {
    fetchScheduledContent();
    fetchTemplates();
  }, []);

  const fetchScheduledContent = async () => {
    try {
      const response = await axios.get(`${API}/content/scheduled`);
      setScheduledContent(response.data);
    } catch (error) {
      console.error('Error fetching scheduled content:', error);
    }
  };

  const fetchTemplates = async () => {
    try {
      const response = await axios.get(`${API}/content/templates`);
      setTemplates(response.data);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  };

  const handleScheduleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const formData = new FormData();
      formData.append('title', scheduleForm.title);
      formData.append('description', scheduleForm.description);
      formData.append('scheduled_date', `${scheduleForm.scheduled_date}T${scheduleForm.scheduled_time}:00Z`);
      formData.append('is_premium', scheduleForm.is_premium);
      formData.append('is_ppv', scheduleForm.is_ppv);
      formData.append('ppv_price', scheduleForm.ppv_price || '0');
      formData.append('tags', scheduleForm.tags);
      formData.append('is_recurring', scheduleForm.is_recurring);
      formData.append('recurrence_type', scheduleForm.recurrence_type || '');
      formData.append('recurrence_end_date', scheduleForm.recurrence_end_date ? `${scheduleForm.recurrence_end_date}T23:59:59Z` : '');
      
      if (scheduleForm.file) {
        formData.append('file', scheduleForm.file);
      }

      if (editingContent) {
        await axios.put(`${API}/content/scheduled/${editingContent.id}`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        toast({ title: "¡Contenido programado actualizado!" });
      } else {
        await axios.post(`${API}/content/schedule`, formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        });
        toast({ title: "¡Contenido programado exitosamente!" });
      }

      // Reset form
      setScheduleForm({
        title: '',
        description: '',
        scheduled_date: '',
        scheduled_time: '',
        is_premium: false,
        is_ppv: false,
        ppv_price: '',
        tags: '',
        file: null,
        is_recurring: false,
        recurrence_type: '',
        recurrence_end_date: ''
      });

      setShowScheduleModal(false);
      setEditingContent(null);
      fetchScheduledContent();
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al programar contenido",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleTemplateSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await axios.post(`${API}/content/templates`, {
        name: templateForm.name,
        title_template: templateForm.title_template,
        description_template: templateForm.description_template,
        tags: templateForm.tags.split(',').map(tag => tag.trim()).filter(tag => tag),
        is_premium: templateForm.is_premium,
        is_ppv: templateForm.is_ppv,
        ppv_price: templateForm.ppv_price ? parseFloat(templateForm.ppv_price) : null
      });

      toast({ title: "¡Template creado exitosamente!" });

      // Reset form
      setTemplateForm({
        name: '',
        title_template: '',
        description_template: '',
        tags: '',
        is_premium: false,
        is_ppv: false,
        ppv_price: ''
      });

      fetchTemplates();
    } catch (error) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Error al crear template",
        variant: "destructive"
      });
    } finally {
      setLoading(false);
    }
  };

  const handleCancelScheduled = async (contentId) => {
    try {
      await axios.delete(`${API}/content/scheduled/${contentId}`);
      toast({ title: "Contenido programado cancelado" });
      fetchScheduledContent();
    } catch (error) {
      toast({
        title: "Error",
        description: "Error al cancelar contenido programado",
        variant: "destructive"
      });
    }
  };

  const handleEditScheduled = (content) => {
    setEditingContent(content);
    setScheduleForm({
      title: content.title,
      description: content.description,
      scheduled_date: content.scheduled_date.split('T')[0],
      scheduled_time: content.scheduled_date.split('T')[1].substring(0, 5),
      is_premium: content.is_premium,
      is_ppv: content.is_ppv,
      ppv_price: content.ppv_price?.toString() || '',
      tags: content.tags.join(', '),
      file: null,
      is_recurring: content.is_recurring,
      recurrence_type: content.recurrence_type || '',
      recurrence_end_date: content.recurrence_end_date ? content.recurrence_end_date.split('T')[0] : ''
    });
    setShowScheduleModal(true);
  };

  const useTemplate = (template) => {
    setScheduleForm({
      ...scheduleForm,
      title: template.title_template,
      description: template.description_template,
      tags: template.tags.join(', '),
      is_premium: template.is_premium,
      is_ppv: template.is_ppv,
      ppv_price: template.ppv_price?.toString() || ''
    });
    setShowScheduleModal(true);
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'scheduled': return 'bg-blue-100 text-blue-800';
      case 'published': return 'bg-green-100 text-green-800';
      case 'cancelled': return 'bg-gray-100 text-gray-800';
      case 'failed': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('es-ES', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (!user?.is_creator) {
    return (
      <div className="max-w-2xl mx-auto py-16 px-4 text-center">
        <div className="bg-yellow-100 rounded-full w-16 h-16 flex items-center justify-center mx-auto mb-6">
          <CalendarIcon className="h-8 w-8 text-yellow-600" />
        </div>
        <h1 className="text-2xl font-bold text-slate-900 mb-4">Acceso de Creador Requerido</h1>
        <p className="text-slate-600 mb-8">Esta función está disponible solo para creadores.</p>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900 mb-2">Programación de Contenido</h1>
        <p className="text-slate-600">Automatiza y programa tu contenido para publicación automática</p>
      </div>

      <Tabs defaultValue="schedule">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="schedule">Programar Contenido</TabsTrigger>
          <TabsTrigger value="scheduled">Contenido Programado</TabsTrigger>
          <TabsTrigger value="templates">Templates</TabsTrigger>
        </TabsList>

        {/* Schedule Content Tab */}
        <TabsContent value="schedule">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Calendar */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center">
                  <CalendarIcon className="h-5 w-5 mr-2" />
                  Calendario de Publicación
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Calendar
                  mode="single"
                  selected={selectedDate}
                  onSelect={setSelectedDate}
                  className="rounded-md border"
                />
                <div className="mt-4">
                  <Button 
                    onClick={() => setShowScheduleModal(true)} 
                    className="w-full"
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Programar Nuevo Contenido
                  </Button>
                </div>
              </CardContent>
            </Card>

            {/* Quick Actions */}
            <Card>
              <CardHeader>
                <CardTitle>Acciones Rápidas</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <Button variant="outline" className="h-auto p-4 flex flex-col items-center">
                    <Repeat className="h-6 w-6 mb-2 text-blue-600" />
                    <span className="text-sm font-medium">Contenido Recurrente</span>
                    <span className="text-xs text-slate-500">Programa series</span>
                  </Button>
                  <Button variant="outline" className="h-auto p-4 flex flex-col items-center">
                    <Save className="h-6 w-6 mb-2 text-green-600" />
                    <span className="text-sm font-medium">Usar Template</span>
                    <span className="text-xs text-slate-500">Plantillas guardadas</span>
                  </Button>
                </div>

                {/* Templates Preview */}
                <div className="space-y-2">
                  <h4 className="font-medium text-slate-900">Templates Disponibles:</h4>
                  {templates.slice(0, 3).map(template => (
                    <div key={template.id} className="flex items-center justify-between p-2 border rounded">
                      <span className="text-sm text-slate-700">{template.name}</span>
                      <Button 
                        size="sm" 
                        variant="ghost"
                        onClick={() => useTemplate(template)}
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Scheduled Content Tab */}
        <TabsContent value="scheduled">
          <Card>
            <CardHeader>
              <CardTitle>Contenido Programado</CardTitle>
              <CardDescription>
                Gestiona tu contenido programado para publicación automática
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {scheduledContent.length === 0 ? (
                  <div className="text-center py-8">
                    <Clock className="h-12 w-12 text-slate-400 mx-auto mb-4" />
                    <h3 className="text-lg font-medium text-slate-900 mb-2">No hay contenido programado</h3>
                    <p className="text-slate-600">Programa tu primer contenido para empezar</p>
                  </div>
                ) : (
                  scheduledContent.map(content => (
                    <div key={content.id} className="border rounded-lg p-4 hover:shadow-md transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-2">
                            <h4 className="font-medium text-slate-900">{content.title}</h4>
                            <Badge className={getStatusColor(content.status)}>
                              {content.status}
                            </Badge>
                            {content.is_recurring && (
                              <Badge variant="outline">
                                <Repeat className="h-3 w-3 mr-1" />
                                Recurrente
                              </Badge>
                            )}
                          </div>
                          <p className="text-sm text-slate-600 mb-2">{content.description}</p>
                          <div className="flex items-center gap-4 text-xs text-slate-500">
                            <span className="flex items-center">
                              <CalendarIcon className="h-3 w-3 mr-1" />
                              {formatDate(content.scheduled_date)}
                            </span>
                            {content.tags.length > 0 && (
                              <span>Tags: {content.tags.join(', ')}</span>
                            )}
                            {content.is_premium && <span className="text-yellow-600">Premium</span>}
                            {content.is_ppv && <span className="text-green-600">PPV: ${content.ppv_price}</span>}
                          </div>
                        </div>
                        
                        <div className="flex items-center gap-2">
                          {content.status === 'scheduled' && (
                            <>
                              <Button 
                                size="sm" 
                                variant="ghost"
                                onClick={() => handleEditScheduled(content)}
                              >
                                <Edit3 className="h-4 w-4" />
                              </Button>
                              <Button 
                                size="sm" 
                                variant="ghost"
                                onClick={() => handleCancelScheduled(content.id)}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Templates Tab */}
        <TabsContent value="templates">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Create Template */}
            <Card>
              <CardHeader>
                <CardTitle>Crear Template</CardTitle>
                <CardDescription>
                  Crea plantillas para reutilizar en contenido futuro
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleTemplateSubmit} className="space-y-4">
                  <div>
                    <Label htmlFor="template_name">Nombre del Template</Label>
                    <Input
                      id="template_name"
                      value={templateForm.name}
                      onChange={(e) => setTemplateForm({ ...templateForm, name: e.target.value })}
                      placeholder="Ej: Post Motivacional Lunes"
                      required
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="title_template">Plantilla de Título</Label>
                    <Input
                      id="title_template"
                      value={templateForm.title_template}
                      onChange={(e) => setTemplateForm({ ...templateForm, title_template: e.target.value })}
                      placeholder="Ej: Motivación del {día}"
                      required
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="description_template">Plantilla de Descripción</Label>
                    <Textarea
                      id="description_template"
                      value={templateForm.description_template}
                      onChange={(e) => setTemplateForm({ ...templateForm, description_template: e.target.value })}
                      placeholder="Descripción con variables..."
                      rows={3}
                      required
                    />
                  </div>
                  
                  <div>
                    <Label htmlFor="template_tags">Tags</Label>
                    <Input
                      id="template_tags"
                      value={templateForm.tags}
                      onChange={(e) => setTemplateForm({ ...templateForm, tags: e.target.value })}
                      placeholder="motivación, lunes, fitness"
                    />
                  </div>

                  <div className="space-y-3">
                    <div className="flex items-center space-x-2">
                      <Switch
                        id="template_premium"
                        checked={templateForm.is_premium}
                        onCheckedChange={(checked) => setTemplateForm({ ...templateForm, is_premium: checked })}
                      />
                      <Label htmlFor="template_premium">Contenido Premium</Label>
                    </div>

                    <div className="flex items-center space-x-2">
                      <Switch
                        id="template_ppv"
                        checked={templateForm.is_ppv}
                        onCheckedChange={(checked) => setTemplateForm({ ...templateForm, is_ppv: checked })}
                      />
                      <Label htmlFor="template_ppv">Pago por Visualización</Label>
                    </div>

                    {templateForm.is_ppv && (
                      <div>
                        <Label htmlFor="template_ppv_price">Precio PPV ($USD)</Label>
                        <Input
                          id="template_ppv_price"
                          type="number"
                          step="0.01"
                          value={templateForm.ppv_price}
                          onChange={(e) => setTemplateForm({ ...templateForm, ppv_price: e.target.value })}
                          placeholder="5.00"
                        />
                      </div>
                    )}
                  </div>

                  <Button type="submit" disabled={loading} className="w-full">
                    {loading ? 'Creando...' : 'Crear Template'}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {/* Templates List */}
            <Card>
              <CardHeader>
                <CardTitle>Mis Templates</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {templates.map(template => (
                    <div key={template.id} className="border rounded p-3 hover:shadow-sm transition-shadow">
                      <div className="flex items-start justify-between">
                        <div className="flex-1">
                          <h4 className="font-medium text-slate-900 mb-1">{template.name}</h4>
                          <p className="text-sm text-slate-600 mb-2">{template.title_template}</p>
                          <div className="flex flex-wrap gap-1">
                            {template.tags.map(tag => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={() => useTemplate(template)}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                          <Button 
                            size="sm" 
                            variant="ghost"
                            onClick={async () => {
                              try {
                                await axios.delete(`${API}/content/templates/${template.id}`);
                                toast({ title: "Template eliminado" });
                                fetchTemplates();
                              } catch (error) {
                                toast({ title: "Error al eliminar template", variant: "destructive" });
                              }
                            }}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Schedule Content Modal */}
      <Dialog open={showScheduleModal} onOpenChange={setShowScheduleModal}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>
              {editingContent ? 'Editar Contenido Programado' : 'Programar Nuevo Contenido'}
            </DialogTitle>
            <DialogDescription>
              Define cuándo y cómo se publicará tu contenido automáticamente
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleScheduleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="schedule_title">Título *</Label>
                <Input
                  id="schedule_title"
                  value={scheduleForm.title}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, title: e.target.value })}
                  required
                />
              </div>
              
              <div>
                <Label htmlFor="schedule_tags">Tags</Label>
                <Input
                  id="schedule_tags"
                  value={scheduleForm.tags}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, tags: e.target.value })}
                  placeholder="fitness, lifestyle, motivación"
                />
              </div>
            </div>

            <div>
              <Label htmlFor="schedule_description">Descripción *</Label>
              <Textarea
                id="schedule_description"
                value={scheduleForm.description}
                onChange={(e) => setScheduleForm({ ...scheduleForm, description: e.target.value })}
                rows={3}
                required
              />
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <Label htmlFor="schedule_date">Fecha de Publicación *</Label>
                <Input
                  id="schedule_date"
                  type="date"
                  value={scheduleForm.scheduled_date}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, scheduled_date: e.target.value })}
                  required
                />
              </div>
              
              <div>
                <Label htmlFor="schedule_time">Hora de Publicación *</Label>
                <Input
                  id="schedule_time"
                  type="time"
                  value={scheduleForm.scheduled_time}
                  onChange={(e) => setScheduleForm({ ...scheduleForm, scheduled_time: e.target.value })}
                  required
                />
              </div>
            </div>

            <div>
              <Label htmlFor="schedule_file">Archivo (opcional)</Label>
              <Input
                id="schedule_file"
                type="file"
                accept="image/*,video/*,audio/*"
                onChange={(e) => setScheduleForm({ ...scheduleForm, file: e.target.files[0] })}
              />
            </div>

            {/* Recurring Content */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Switch
                  id="schedule_recurring"
                  checked={scheduleForm.is_recurring}
                  onCheckedChange={(checked) => setScheduleForm({ ...scheduleForm, is_recurring: checked })}
                />
                <Label htmlFor="schedule_recurring">Contenido Recurrente</Label>
              </div>

              {scheduleForm.is_recurring && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 ml-6">
                  <div>
                    <Label htmlFor="recurrence_type">Frecuencia</Label>
                    <Select value={scheduleForm.recurrence_type} onValueChange={(value) => setScheduleForm({ ...scheduleForm, recurrence_type: value })}>
                      <SelectTrigger>
                        <SelectValue placeholder="Selecciona frecuencia" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="daily">Diario</SelectItem>
                        <SelectItem value="weekly">Semanal</SelectItem>
                        <SelectItem value="monthly">Mensual</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  
                  <div>
                    <Label htmlFor="recurrence_end">Fecha de Fin (opcional)</Label>
                    <Input
                      id="recurrence_end"
                      type="date"
                      value={scheduleForm.recurrence_end_date}
                      onChange={(e) => setScheduleForm({ ...scheduleForm, recurrence_end_date: e.target.value })}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Premium Options */}
            <div className="space-y-3">
              <div className="flex items-center space-x-2">
                <Switch
                  id="schedule_premium"
                  checked={scheduleForm.is_premium}
                  onCheckedChange={(checked) => setScheduleForm({ ...scheduleForm, is_premium: checked })}
                />
                <Label htmlFor="schedule_premium">Contenido Premium</Label>
              </div>

              <div className="flex items-center space-x-2">
                <Switch
                  id="schedule_ppv"
                  checked={scheduleForm.is_ppv}
                  onCheckedChange={(checked) => setScheduleForm({ ...scheduleForm, is_ppv: checked })}
                />
                <Label htmlFor="schedule_ppv">Pago por Visualización</Label>
              </div>

              {scheduleForm.is_ppv && (
                <div className="ml-6">
                  <Label htmlFor="schedule_ppv_price">Precio PPV ($USD)</Label>
                  <Input
                    id="schedule_ppv_price"
                    type="number"
                    step="0.01"
                    value={scheduleForm.ppv_price}
                    onChange={(e) => setScheduleForm({ ...scheduleForm, ppv_price: e.target.value })}
                    placeholder="5.00"
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end gap-2 pt-4">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => {
                  setShowScheduleModal(false);
                  setEditingContent(null);
                }}
              >
                Cancelar
              </Button>
              <Button type="submit" disabled={loading}>
                {loading ? 'Guardando...' : (editingContent ? 'Actualizar' : 'Programar')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ContentScheduler;