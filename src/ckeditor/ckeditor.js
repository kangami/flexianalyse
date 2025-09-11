import ClassicEditorBase from '@ckeditor/ckeditor5-editor-classic/src/classiceditor';

import Essentials from '@ckeditor/ckeditor5-essentials/src/essentials';
import Bold from '@ckeditor/ckeditor5-basic-styles/src/bold';
import Italic from '@ckeditor/ckeditor5-basic-styles/src/italic';
import Underline from '@ckeditor/ckeditor5-basic-styles/src/underline';
import Strikethrough from '@ckeditor/ckeditor5-basic-styles/src/strikethrough';
import Paragraph from '@ckeditor/ckeditor5-paragraph/src/paragraph';
import List from '@ckeditor/ckeditor5-list/src/list';
import Undo from '@ckeditor/ckeditor5-undo/src/undo';  // ✅ à la place de Redo
import Heading from '@ckeditor/ckeditor5-heading/src/heading';

export default class ClassicEditor extends ClassicEditorBase {}

ClassicEditor.builtinPlugins = [
  Essentials,
  Bold,
  Italic,
  Underline,
  Strikethrough,
  Paragraph,
  List,
  Undo,  // ✅ on garde juste Undo
  Heading
];

ClassicEditor.defaultConfig = {
  toolbar: {
    items: [
      'heading', '|',
      'bold', 'italic', 'underline', 'strikethrough', '|',
      'bulletedList', 'numberedList', '|',
      'undo', 'redo'  // ✅ fonctionne car Undo fournit les deux commandes
    ]
  },
  language: 'en'
};