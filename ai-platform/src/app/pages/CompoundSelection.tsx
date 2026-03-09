import { useState } from 'react';
import { useNavigate } from 'react-router';
import { compounds } from '../data/compounds';
import { Compound } from '../types/compound';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Database, Search, Pill, ArrowRight, Beaker } from 'lucide-react';

export default function CompoundSelection() {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [therapeuticAreaFilter, setTherapeuticAreaFilter] = useState<string>('all');
  const [stageFilter, setStageFilter] = useState<string>('all');

  const therapeuticAreas = Array.from(new Set(compounds.map(c => c.therapeuticArea))).sort();
  const stages = Array.from(new Set(compounds.map(c => c.stage))).sort();

  const filteredCompounds = compounds.filter(compound => {
    const matchesSearch = 
      compound.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      compound.genericName.toLowerCase().includes(searchQuery.toLowerCase()) ||
      compound.indication.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesTherapeuticArea = therapeuticAreaFilter === 'all' || compound.therapeuticArea === therapeuticAreaFilter;
    const matchesStage = stageFilter === 'all' || compound.stage === stageFilter;
    
    return matchesSearch && matchesTherapeuticArea && matchesStage;
  });

  const getStageColor = (stage: string): string => {
    switch (stage) {
      case 'Discovery':
      case 'Preclinical':
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
      case 'Phase I':
      case 'Phase II':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'Phase III':
        return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'Approved':
      case 'Marketed':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      default:
        return 'bg-gray-500/10 text-gray-500 border-gray-500/20';
    }
  };

  const handleSelectCompound = (compoundId: string) => {
    navigate(`/knowledge/${compoundId}`);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      <div className="container mx-auto px-4 py-8">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <Database className="h-8 w-8 text-primary" />
            <h1 className="text-4xl">Knowledge Base</h1>
          </div>
          <p className="text-muted-foreground">
            Select a compound to access and manage its knowledge base
          </p>
        </div>

        <div className="mb-8 flex flex-col gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search compounds by name, generic name, or indication..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          
          <div className="flex flex-col md:flex-row gap-4">
            <Select value={therapeuticAreaFilter} onValueChange={setTherapeuticAreaFilter}>
              <SelectTrigger className="w-full md:w-[250px]">
                <SelectValue placeholder="Therapeutic Area" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Therapeutic Areas</SelectItem>
                {therapeuticAreas.map(area => (
                  <SelectItem key={area} value={area}>{area}</SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={stageFilter} onValueChange={setStageFilter}>
              <SelectTrigger className="w-full md:w-[250px]">
                <SelectValue placeholder="Development Stage" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Stages</SelectItem>
                {stages.map(stage => (
                  <SelectItem key={stage} value={stage}>{stage}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredCompounds.map(compound => (
            <Card key={compound.id} className="hover:shadow-lg transition-shadow group cursor-pointer" onClick={() => handleSelectCompound(compound.id)}>
              <CardHeader>
                <div className="flex items-start justify-between mb-2">
                  <div className="bg-primary/10 p-2 rounded-lg">
                    <Pill className="h-6 w-6 text-primary" />
                  </div>
                  <Badge variant="outline" className={getStageColor(compound.stage)}>
                    {compound.stage}
                  </Badge>
                </div>
                <CardTitle className="group-hover:text-primary transition-colors">
                  {compound.name}
                </CardTitle>
                <CardDescription className="text-xs">
                  {compound.genericName}
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  <div>
                    <Badge variant="secondary" className="mb-2">
                      {compound.therapeuticArea}
                    </Badge>
                    <p className="text-sm mb-2">
                      <span className="font-medium">Indication:</span> {compound.indication}
                    </p>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    {compound.description}
                  </p>
                  <Button variant="outline" className="w-full group-hover:bg-primary group-hover:text-primary-foreground transition-colors">
                    Access Knowledge Base
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {filteredCompounds.length === 0 && (
          <Card className="border-dashed">
            <CardContent className="flex flex-col items-center justify-center py-12">
              <Beaker className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-muted-foreground text-center">
                No compounds match your search criteria
              </p>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
