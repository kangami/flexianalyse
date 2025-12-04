import React, { useState } from 'react';

interface StructuredData {
  type_document?: string;
  parties?: Array<{
    nom?: string;
    role?: string;
    adresse?: string;
    telephone?: string;
    email?: string;
  }>;
  dates_importantes?: Array<{
    type?: string;
    valeur?: string;
  }>;
  montants?: Array<{
    type?: string;
    valeur?: number | string;
    devise?: string;
  }>;
  bien_loue?: {
    adresse?: string;
    superficie?: string;
    type?: string;
  };
  clauses_cles?: string[];
  conditions?: string[];
  employeur?: {
    nom?: string;
    adresse?: string;
    siret?: string;
  };
  employe?: {
    nom?: string;
    adresse?: string;
    poste?: string;
    fonctions?: string;
  };
  remuneration?: {
    salaire_brut_mensuel?: number;
    salaire_net_mensuel?: number;
    devise?: string;
    avantages?: string[];
  };
  duree?: {
    type?: string;
    duree?: string;
  };
  testateur?: {
    nom?: string;
    adresse?: string;
    date_naissance?: string;
  };
  beneficiaires?: Array<{
    nom?: string;
    relation?: string;
    legs?: string;
    conditions?: string;
  }>;
  executeur_testamentaire?: {
    nom?: string;
    fonctions?: string;
  };
  biens_legues?: Array<{
    description?: string;
    beneficiaire?: string;
    valeur_estimee?: string;
  }>;
  objet?: string;
  obligations?: string[];
  informations_cles?: string[];
  metadata?: {
    file_name?: string;
    document_type?: string;
    extraction_date?: string;
  };
}

interface StructuredDataDisplayProps {
  data: StructuredData;
  onClose: () => void;
}

const StructuredDataDisplay: React.FC<StructuredDataDisplayProps> = ({ data, onClose }) => {
  const [activeTab, setActiveTab] = useState<string>('overview');

  const exportToJSON = () => {
    const jsonStr = JSON.stringify(data, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.metadata?.file_name || 'extraction'}_structured.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const exportToCSV = () => {
    let csv = '';
    
    // Parties
    if (data.parties && data.parties.length > 0) {
      csv += 'PARTIES\n';
      csv += 'Nom,Rôle,Adresse,Téléphone,Email\n';
      data.parties.forEach(party => {
        csv += `"${party.nom || ''}","${party.role || ''}","${party.adresse || ''}","${party.telephone || ''}","${party.email || ''}"\n`;
      });
      csv += '\n';
    }

    // Dates
    if (data.dates_importantes && data.dates_importantes.length > 0) {
      csv += 'DATES IMPORTANTES\n';
      csv += 'Type,Valeur\n';
      data.dates_importantes.forEach(date => {
        csv += `"${date.type || ''}","${date.valeur || ''}"\n`;
      });
      csv += '\n';
    }

    // Montants
    if (data.montants && data.montants.length > 0) {
      csv += 'MONTANTS\n';
      csv += 'Type,Valeur,Devise\n';
      data.montants.forEach(montant => {
        csv += `"${montant.type || ''}","${montant.valeur || ''}","${montant.devise || ''}"\n`;
      });
      csv += '\n';
    }

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${data.metadata?.file_name || 'extraction'}_structured.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const renderSection = (title: string, content: React.ReactNode) => (
    <div className="mb-6">
      <h3 className="text-lg font-semibold text-gray-800 mb-3 border-b border-gray-200 pb-2">
        {title}
      </h3>
      {content}
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b border-gray-200 bg-gray-50">
          <div>
            <h2 className="text-xl font-bold text-gray-800">
              📋 Données structurées extraites
            </h2>
            <p className="text-sm text-gray-600 mt-1">
              {data.metadata?.file_name || 'Document'}
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={exportToJSON}
              className="px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 text-sm font-medium"
              title="Exporter en JSON"
            >
              📥 JSON
            </button>
            <button
              onClick={exportToCSV}
              className="px-3 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 text-sm font-medium"
              title="Exporter en CSV"
            >
              📊 CSV
            </button>
            <button
              onClick={onClose}
              className="px-3 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 text-sm font-medium"
            >
              ✕ Fermer
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Type de document */}
          {data.type_document && (
            <div className="mb-4 p-3 bg-blue-50 rounded-lg border border-blue-200">
              <span className="text-sm font-semibold text-blue-800">Type de document: </span>
              <span className="text-sm text-blue-600">{data.type_document}</span>
            </div>
          )}

          {/* Parties */}
          {data.parties && data.parties.length > 0 && renderSection(
            '👥 Parties',
            <div className="space-y-3">
              {data.parties.map((party, index) => (
                <div key={index} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    <div>
                      <span className="font-semibold text-gray-700">Nom: </span>
                      <span className="text-gray-900">{party.nom || 'N/A'}</span>
                    </div>
                    <div>
                      <span className="font-semibold text-gray-700">Rôle: </span>
                      <span className="text-gray-900">{party.role || 'N/A'}</span>
                    </div>
                    {party.adresse && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-gray-700">Adresse: </span>
                        <span className="text-gray-900">{party.adresse}</span>
                      </div>
                    )}
                    {party.telephone && (
                      <div>
                        <span className="font-semibold text-gray-700">Téléphone: </span>
                        <span className="text-gray-900">{party.telephone}</span>
                      </div>
                    )}
                    {party.email && (
                      <div>
                        <span className="font-semibold text-gray-700">Email: </span>
                        <span className="text-gray-900">{party.email}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Employeur/Employé (contrat de travail) */}
          {(data.employeur || data.employe) && renderSection(
            '💼 Informations professionnelles',
            <div className="space-y-3">
              {data.employeur && (
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <h4 className="font-semibold text-gray-800 mb-2">Employeur</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {data.employeur.nom && (
                      <div>
                        <span className="font-semibold text-gray-700">Nom: </span>
                        <span className="text-gray-900">{data.employeur.nom}</span>
                      </div>
                    )}
                    {data.employeur.adresse && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-gray-700">Adresse: </span>
                        <span className="text-gray-900">{data.employeur.adresse}</span>
                      </div>
                    )}
                    {data.employeur.siret && (
                      <div>
                        <span className="font-semibold text-gray-700">SIRET: </span>
                        <span className="text-gray-900">{data.employeur.siret}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
              {data.employe && (
                <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <h4 className="font-semibold text-gray-800 mb-2">Employé</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {data.employe.nom && (
                      <div>
                        <span className="font-semibold text-gray-700">Nom: </span>
                        <span className="text-gray-900">{data.employe.nom}</span>
                      </div>
                    )}
                    {data.employe.poste && (
                      <div>
                        <span className="font-semibold text-gray-700">Poste: </span>
                        <span className="text-gray-900">{data.employe.poste}</span>
                      </div>
                    )}
                    {data.employe.fonctions && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-gray-700">Fonctions: </span>
                        <span className="text-gray-900">{data.employe.fonctions}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Dates importantes */}
          {data.dates_importantes && data.dates_importantes.length > 0 && renderSection(
            '📅 Dates importantes',
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.dates_importantes.map((date, index) => (
                <div key={index} className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                  <div className="font-semibold text-gray-700 text-sm">{date.type || 'Date'}</div>
                  <div className="text-gray-900 font-medium">{date.valeur || 'N/A'}</div>
                </div>
              ))}
            </div>
          )}

          {/* Montants */}
          {data.montants && data.montants.length > 0 && renderSection(
            '💰 Montants',
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {data.montants.map((montant, index) => (
                <div key={index} className="bg-gray-50 p-3 rounded-lg border border-gray-200">
                  <div className="font-semibold text-gray-700 text-sm">{montant.type || 'Montant'}</div>
                  <div className="text-gray-900 font-medium text-lg">
                    {typeof montant.valeur === 'number' && montant.valeur !== null
                      ? montant.valeur.toLocaleString('fr-FR') 
                      : montant.valeur || 'N/A'} {montant.devise || '€'}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Rémunération (contrat de travail) */}
          {data.remuneration && renderSection(
            '💵 Rémunération',
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {data.remuneration.salaire_brut_mensuel !== undefined && data.remuneration.salaire_brut_mensuel !== null && typeof data.remuneration.salaire_brut_mensuel === 'number' && (
                  <div>
                    <span className="font-semibold text-gray-700">Salaire brut mensuel: </span>
                    <span className="text-gray-900 font-medium">
                      {data.remuneration.salaire_brut_mensuel.toLocaleString('fr-FR')} {data.remuneration.devise || '€'}
                    </span>
                  </div>
                )}
                {data.remuneration.salaire_net_mensuel !== undefined && data.remuneration.salaire_net_mensuel !== null && typeof data.remuneration.salaire_net_mensuel === 'number' && (
                  <div>
                    <span className="font-semibold text-gray-700">Salaire net mensuel: </span>
                    <span className="text-gray-900 font-medium">
                      {data.remuneration.salaire_net_mensuel.toLocaleString('fr-FR')} {data.remuneration.devise || '€'}
                    </span>
                  </div>
                )}
                {data.remuneration.avantages && data.remuneration.avantages.length > 0 && (
                  <div className="md:col-span-2">
                    <span className="font-semibold text-gray-700">Avantages: </span>
                    <ul className="list-disc list-inside mt-1">
                      {data.remuneration.avantages.map((avantage, idx) => (
                        <li key={idx} className="text-gray-900">{avantage}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Bien loué */}
          {data.bien_loue && renderSection(
            '🏠 Bien loué',
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {data.bien_loue.adresse && (
                  <div className="md:col-span-2">
                    <span className="font-semibold text-gray-700">Adresse: </span>
                    <span className="text-gray-900">{data.bien_loue.adresse}</span>
                  </div>
                )}
                {data.bien_loue.superficie && (
                  <div>
                    <span className="font-semibold text-gray-700">Superficie: </span>
                    <span className="text-gray-900">{data.bien_loue.superficie}</span>
                  </div>
                )}
                {data.bien_loue.type && (
                  <div>
                    <span className="font-semibold text-gray-700">Type: </span>
                    <span className="text-gray-900">{data.bien_loue.type}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Clauses clés */}
          {data.clauses_cles && data.clauses_cles.length > 0 && renderSection(
            '📜 Clauses clés',
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <ul className="list-disc list-inside space-y-2">
                {data.clauses_cles.map((clause, index) => (
                  <li key={index} className="text-gray-900">{clause}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Conditions */}
          {data.conditions && data.conditions.length > 0 && renderSection(
            '⚖️ Conditions',
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <ul className="list-disc list-inside space-y-2">
                {data.conditions.map((condition, index) => (
                  <li key={index} className="text-gray-900">{condition}</li>
                ))}
              </ul>
            </div>
          )}

          {/* Testateur (testament) */}
          {data.testateur && renderSection(
            '👤 Testateur',
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {data.testateur.nom && (
                  <div>
                    <span className="font-semibold text-gray-700">Nom: </span>
                    <span className="text-gray-900">{data.testateur.nom}</span>
                  </div>
                )}
                {data.testateur.adresse && (
                  <div className="md:col-span-2">
                    <span className="font-semibold text-gray-700">Adresse: </span>
                    <span className="text-gray-900">{data.testateur.adresse}</span>
                  </div>
                )}
                {data.testateur.date_naissance && (
                  <div>
                    <span className="font-semibold text-gray-700">Date de naissance: </span>
                    <span className="text-gray-900">{data.testateur.date_naissance}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Bénéficiaires (testament) */}
          {data.beneficiaires && data.beneficiaires.length > 0 && renderSection(
            '🎁 Bénéficiaires',
            <div className="space-y-3">
              {data.beneficiaires.map((beneficiaire, index) => (
                <div key={index} className="bg-gray-50 p-4 rounded-lg border border-gray-200">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {beneficiaire.nom && (
                      <div>
                        <span className="font-semibold text-gray-700">Nom: </span>
                        <span className="text-gray-900">{beneficiaire.nom}</span>
                      </div>
                    )}
                    {beneficiaire.relation && (
                      <div>
                        <span className="font-semibold text-gray-700">Relation: </span>
                        <span className="text-gray-900">{beneficiaire.relation}</span>
                      </div>
                    )}
                    {beneficiaire.legs && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-gray-700">Legs: </span>
                        <span className="text-gray-900">{beneficiaire.legs}</span>
                      </div>
                    )}
                    {beneficiaire.conditions && (
                      <div className="md:col-span-2">
                        <span className="font-semibold text-gray-700">Conditions: </span>
                        <span className="text-gray-900">{beneficiaire.conditions}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Informations clés (document générique) */}
          {data.informations_cles && data.informations_cles.length > 0 && renderSection(
            '🔑 Informations clés',
            <div className="bg-gray-50 p-4 rounded-lg border border-gray-200">
              <ul className="list-disc list-inside space-y-2">
                {data.informations_cles.map((info, index) => (
                  <li key={index} className="text-gray-900">{info}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default StructuredDataDisplay;

