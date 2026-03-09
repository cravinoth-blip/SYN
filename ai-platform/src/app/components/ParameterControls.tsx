import { GenerationParams } from '../types/template';
import { Label } from './ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Card, CardHeader, CardTitle, CardContent } from './ui/card';
import { Sliders } from 'lucide-react';

interface ParameterControlsProps {
  params: GenerationParams;
  onChange: (params: GenerationParams) => void;
}

export function ParameterControls({ params, onChange }: ParameterControlsProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sliders className="h-5 w-5" />
          Generation Parameters
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="tone">Tone</Label>
          <Select 
            value={params.tone} 
            onValueChange={(value) => onChange({ ...params, tone: value as GenerationParams['tone'] })}
          >
            <SelectTrigger id="tone">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="professional">Professional</SelectItem>
              <SelectItem value="casual">Casual</SelectItem>
              <SelectItem value="friendly">Friendly</SelectItem>
              <SelectItem value="formal">Formal</SelectItem>
              <SelectItem value="creative">Creative</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="length">Length</Label>
          <Select 
            value={params.length} 
            onValueChange={(value) => onChange({ ...params, length: value as GenerationParams['length'] })}
          >
            <SelectTrigger id="length">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="short">Short</SelectItem>
              <SelectItem value="medium">Medium</SelectItem>
              <SelectItem value="long">Long</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label htmlFor="style">Style</Label>
          <Select 
            value={params.style} 
            onValueChange={(value) => onChange({ ...params, style: value as GenerationParams['style'] })}
          >
            <SelectTrigger id="style">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="descriptive">Descriptive</SelectItem>
              <SelectItem value="concise">Concise</SelectItem>
              <SelectItem value="persuasive">Persuasive</SelectItem>
              <SelectItem value="informative">Informative</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </CardContent>
    </Card>
  );
}
