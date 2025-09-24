import React from 'react';

const PrivacyPolicy = () => {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-6">Politique de confidentialité</h1>
      <p className="mb-4 text-gray-600">Dernière mise à jour : 24 septembre 2025</p>

      <div className="space-y-8">
        {/* Introduction */}
        <section>
          <p className="mb-4">
            Chez <strong>FlexiAnalyse</strong> (ci-après "nous", "notre" ou "la Société"), nous nous engageons à protéger et respecter votre vie privée. Cette politique de confidentialité explique comment nous collectons, utilisons, stockons et protégeons vos informations personnelles lorsque vous utilisez notre plateforme d'analyse de documents basée sur l'IA accessible à l'adresse <a href="https://flexianalyse.com" className="text-blue-600 hover:underline">flexianalyse.com</a>.
          </p>
          <p className="mb-4">
            En utilisant nos services, vous acceptez les pratiques décrites dans cette politique. Si vous n'acceptez pas cette politique, veuillez ne pas utiliser nos services.
          </p>
        </section>

        {/* 1. Informations que nous collectons */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">1. Informations que nous collectons</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">1.1 Informations d'authentification Google</h3>
          <p className="mb-4">
            Lorsque vous vous connectez via Google OAuth, nous collectons :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Votre adresse email Google</li>
            <li>Votre nom complet</li>
            <li>Votre photo de profil (optionnelle)</li>
            <li>Un identifiant Google unique</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">1.2 Données d'utilisation</h3>
          <p className="mb-4">
            Nous collectons automatiquement certaines informations lorsque vous utilisez notre service :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Adresse IP</li>
            <li>Type de navigateur et version</li>
            <li>Système d'exploitation</li>
            <li>Pages visitées et temps passé sur le site</li>
            <li>Actions effectuées sur la plateforme</li>
            <li>Horodatage des connexions</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">1.3 Documents et contenu</h3>
          <p className="mb-4">
            Lorsque vous utilisez notre service d'analyse de documents, nous traitons temporairement :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Les documents que vous téléchargez pour analyse</li>
            <li>Le contenu extrait de ces documents</li>
            <li>Les résultats d'analyse générés par notre IA</li>
            <li>Vos requêtes et interactions avec notre système d'IA</li>
          </ul>
        </section>

        {/* 2. Comment nous utilisons vos informations */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">2. Comment nous utilisons vos informations</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">2.1 Finalités principales</h3>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Authentification et gestion de compte :</strong> Créer et gérer votre compte utilisateur</li>
            <li><strong>Fourniture du service :</strong> Traiter vos documents et fournir des analyses IA</li>
            <li><strong>Support client :</strong> Répondre à vos questions et résoudre les problèmes techniques</li>
            <li><strong>Amélioration du service :</strong> Analyser l'utilisation pour améliorer nos fonctionnalités</li>
            <li><strong>Sécurité :</strong> Détecter et prévenir les activités frauduleuses ou malveillantes</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">2.2 Communications</h3>
          <p className="mb-4">
            Avec votre consentement explicite, nous pouvons vous envoyer :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Notifications sur votre compte et vos analyses</li>
            <li>Mises à jour sur nos services</li>
            <li>Informations marketing sur nos nouveaux produits (désabonnement possible à tout moment)</li>
          </ul>
        </section>

        {/* 3. Base légale du traitement */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">3. Base légale du traitement (RGPD)</h2>
          <p className="mb-4">
            Nous traitons vos données personnelles sur les bases légales suivantes :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Exécution du contrat :</strong> Pour fournir nos services d'analyse de documents</li>
            <li><strong>Consentement :</strong> Pour les communications marketing et l'utilisation de certaines fonctionnalités</li>
            <li><strong>Intérêt légitime :</strong> Pour améliorer nos services et assurer la sécurité</li>
            <li><strong>Obligation légale :</strong> Pour respecter nos obligations réglementaires</li>
          </ul>
        </section>

        {/* 4. Partage et divulgation des données */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">4. Partage et divulgation des données</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">4.1 Principe général</h3>
          <p className="mb-4">
            Nous ne vendons, ne louons, ni ne partageons vos informations personnelles avec des tiers à des fins commerciales.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">4.2 Partages autorisés</h3>
          <p className="mb-4">
            Nous pouvons partager vos données dans les cas suivants :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Prestataires de services :</strong> Avec nos sous-traitants (hébergement cloud, services d'IA) sous contrat de confidentialité</li>
            <li><strong>Obligations légales :</strong> Si requis par la loi, une décision de justice ou une autorité compétente</li>
            <li><strong>Protection des droits :</strong> Pour protéger nos droits, notre propriété ou la sécurité de nos utilisateurs</li>
            <li><strong>Transfert d'entreprise :</strong> En cas de fusion, acquisition ou vente d'actifs</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">4.3 Services tiers utilisés</h3>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li><strong>Google OAuth :</strong> Pour l'authentification (soumis aux politiques de Google)</li>
            <li><strong>OpenAI, Mistral, LLaMA :</strong> Pour les services d'analyse IA</li>
            <li><strong>AWS :</strong> Pour l'hébergement et le stockage sécurisé</li>
            <li><strong>Services d'analytics :</strong> Pour comprendre l'utilisation de notre plateforme</li>
          </ul>
        </section>

        {/* 5. Sécurité et protection des données */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">5. Sécurité et protection des données</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">5.1 Mesures techniques</h3>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Chiffrement SSL/TLS pour toutes les transmissions</li>
            <li>Chiffrement des données au repos</li>
            <li>Authentification à deux facteurs disponible</li>
            <li>Surveillance continue de la sécurité</li>
            <li>Sauvegardes régulières et sécurisées</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">5.2 Mesures organisationnelles</h3>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Accès limité aux données sur la base du besoin de savoir</li>
            <li>Formation régulière du personnel sur la sécurité</li>
            <li>Audits de sécurité réguliers</li>
            <li>Procédures de réponse aux incidents</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">5.3 Traitement des documents</h3>
          <p className="mb-4">
            <strong>Important :</strong> Vos documents sont traités temporairement pour l'analyse et ne sont pas stockés de manière permanente sur nos serveurs. Ils sont supprimés automatiquement après le traitement, sauf si vous choisissez explicitement de les sauvegarder dans votre compte.
          </p>
        </section>

        {/* 6. Conservation des données */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">6. Conservation des données</h2>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Données de compte :</strong> Conservées tant que votre compte est actif</li>
            <li><strong>Documents téléchargés :</strong> Supprimés immédiatement après analyse (sauf sauvegarde explicite)</li>
            <li><strong>Données d'utilisation :</strong> Conservées 24 mois pour l'amélioration du service</li>
            <li><strong>Après suppression de compte :</strong> Toutes les données sont supprimées sous 30 jours</li>
          </ul>
        </section>

        {/* 7. Vos droits */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">7. Vos droits</h2>
          <p className="mb-4">
            Conformément au RGPD et aux lois applicables, vous disposez des droits suivants :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Droit d'accès :</strong> Obtenir une copie de vos données personnelles</li>
            <li><strong>Droit de rectification :</strong> Corriger les données inexactes</li>
            <li><strong>Droit à l'effacement :</strong> Demander la suppression de vos données</li>
            <li><strong>Droit à la portabilité :</strong> Recevoir vos données dans un format structuré</li>
            <li><strong>Droit d'opposition :</strong> S'opposer au traitement pour des raisons légitimes</li>
            <li><strong>Droit de limitation :</strong> Demander la limitation du traitement</li>
            <li><strong>Retrait du consentement :</strong> Retirer votre consentement à tout moment</li>
          </ul>
          <p className="mb-4">
            Pour exercer ces droits, contactez-nous à <a href="mailto:privacy@flexianalyse.com" className="text-blue-600 hover:underline">privacy@flexianalyse.com</a>
          </p>
        </section>

        {/* 8. Transferts internationaux */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">8. Transferts internationaux</h2>
          <p className="mb-4">
            Vos données peuvent être transférées et traitées dans des pays situés en dehors de l'Espace économique européen (EEE), notamment aux États-Unis (services AWS, OpenAI). Ces transferts sont effectués avec des garanties appropriées telles que :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Clauses contractuelles types approuvées par la Commission européenne</li>
            <li>Certifications de nos prestataires (ex: ISO 27001, SOC 2)</li>
            <li>Décisions d'adéquation de la Commission européenne</li>
          </ul>
        </section>

        {/* 9. Cookies et technologies similaires */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">9. Cookies et technologies similaires</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">9.1 Types de cookies utilisés</h3>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Cookies essentiels :</strong> Nécessaires au fonctionnement du site (authentification, sécurité)</li>
            <li><strong>Cookies de performance :</strong> Nous aident à comprendre comment vous utilisez notre site</li>
            <li><strong>Cookies fonctionnels :</strong> Mémorisent vos préférences</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">9.2 Gestion des cookies</h3>
          <p className="mb-4">
            Vous pouvez gérer vos préférences de cookies via les paramètres de votre navigateur. Notez que désactiver certains cookies peut affecter le fonctionnement de notre service.
          </p>
        </section>

        {/* 10. Modifications de cette politique */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">10. Modifications de cette politique</h2>
          <p className="mb-4">
            Nous pouvons modifier cette politique de confidentialité de temps à autre. Les modifications importantes seront communiquées par email ou via une notification sur notre plateforme. La date de dernière mise à jour sera toujours indiquée en haut de cette page.
          </p>
        </section>

        {/* 11. Contact et réclamations */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">11. Contact et réclamations</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">11.1 Délégué à la protection des données</h3>
          <p className="mb-4">
            Pour toute question concernant cette politique de confidentialité ou vos données personnelles :
          </p>
          <div className="bg-gray-50 p-4 rounded-lg mb-4">
            <p><strong>Email :</strong> <a href="mailto:privacy@flexianalyse.com" className="text-blue-600 hover:underline">privacy@flexianalyse.com</a></p>
            <p><strong>Support général :</strong> <a href="mailto:contact@flexianalyse.com" className="text-blue-600 hover:underline">infos@flexianalyse.com</a></p>
            <p><strong>Adresse :</strong> FlexiAnalyse, 8050 Rue Saint Jacques, Canada</p>
          </div>

          <h3 className="text-xl font-medium mt-6 mb-3">11.2 Autorité de contrôle</h3>
          <p className="mb-4">
            Si vous n'êtes pas satisfait de notre réponse, vous avez le droit de déposer une réclamation auprès de l'autorité de protection des données compétente dans votre pays de résidence.
          </p>
        </section>

        {/* 12. Informations légales */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">12. Informations légales</h2>
          <div className="bg-gray-50 p-4 rounded-lg">
            <p><strong>Responsable du traitement :</strong> FlexiAnalyse</p>
            <p><strong>Siège social :</strong> 8050 Rue Saint Jacques, Canada</p>
            <p><strong>Email :</strong> infos@flexianalyse.com</p>
            <p><strong>Téléphone :</strong> 647-321-9396</p>
          </div>
        </section>
      </div>

      <div className="mt-12 pt-6 border-t border-gray-200">
        <p className="text-sm text-gray-600">
          Cette politique de confidentialité a été mise à jour le 24 septembre 2025 pour être conforme au RGPD, 
          à la CCPA et aux exigences de Google OAuth pour les applications publiques.
        </p>
      </div>
    </div>
  );
};

export default PrivacyPolicy;