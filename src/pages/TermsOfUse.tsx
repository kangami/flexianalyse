import React from 'react';

const TermsOfUse = () => {
  return (
    <div className="max-w-4xl mx-auto px-6 py-12">
      <h1 className="text-3xl font-bold mb-6">Conditions d'utilisation</h1>
      <p className="mb-4 text-gray-600">Dernière mise à jour : 24 septembre 2025</p>
      
      <div className="space-y-8">
        {/* Introduction */}
        <section>
          <p className="mb-4">
            Les présentes conditions d'utilisation (les <strong>"Conditions"</strong>) régissent l'utilisation de la plateforme FlexiAnalyse accessible à l'adresse <a href="https://flexianalyse.com" className="text-blue-600 hover:underline">flexianalyse.com</a> (le <strong>"Service"</strong>) exploitée par FlexiAnalyse (ci-après <strong>"nous"</strong>, <strong>"notre"</strong> ou la <strong>"Société"</strong>).
          </p>
          <p className="mb-4">
            En accédant ou en utilisant notre Service, vous acceptez d'être lié par ces Conditions. Si vous n'acceptez pas ces Conditions, vous ne devez pas utiliser le Service.
          </p>
        </section>

        {/* 1. Description du service */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">1. Description du service</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">1.1 Plateforme SaaS</h3>
          <p className="mb-4">
            FlexiAnalyse est une plateforme Software-as-a-Service (SaaS) qui utilise des technologies d'intelligence artificielle pour analyser des documents, extraire des informations et fournir des insights basés sur des modèles de langage avancés (LLM).
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">1.2 Fonctionnalités principales</h3>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Analyse automatisée de documents (PDF, Word, Excel, images, code, etc.)</li>
            <li>Extraction d'informations clés et de données structurées</li>
            <li>Génération de résumés et d'insights via IA</li>
            <li>Interface de requête conversationnelle avec les documents</li>
            <li>Rapports et visualisations de données</li>
            <li>API pour intégrations tierces (selon l'abonnement)</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">1.3 Évolution du service</h3>
          <p className="mb-4">
            Nous nous réservons le droit de modifier, suspendre ou discontinuer tout ou partie du Service à tout moment, avec ou sans préavis. Nous ne serons pas responsables envers vous ou tout tiers pour toute modification, suspension ou discontinuation du Service.
          </p>
        </section>

        {/* 2. Éligibilité et création de compte */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">2. Éligibilité et création de compte</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">2.1 Conditions d'éligibilité</h3>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Vous devez être âgé d'au moins 18 ans</li>
            <li>Vous devez avoir la capacité juridique de conclure un contrat contraignant</li>
            <li>Votre utilisation du Service ne doit pas violer les lois applicables</li>
            <li>Vous ne devez pas être suspendu ou banni du Service</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">2.2 Authentification Google</h3>
          <p className="mb-4">
            L'accès au Service nécessite une authentification via Google OAuth. En utilisant cette méthode d'authentification, vous acceptez également les conditions d'utilisation de Google et reconnaissez que votre utilisation de l'authentification Google est soumise à la politique de confidentialité de Google.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">2.3 Informations de compte</h3>
          <p className="mb-4">
            Vous vous engagez à fournir des informations exactes, complètes et à jour. Vous êtes responsable de maintenir la confidentialité de votre compte et de toutes les activités qui se produisent sous votre compte.
          </p>
        </section>

        {/* 3. Utilisation acceptable */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">3. Utilisation acceptable</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">3.1 Utilisation autorisée</h3>
          <p className="mb-4">
            Vous pouvez utiliser le Service pour :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Analyser vos propres documents ou des documents pour lesquels vous avez les droits nécessaires</li>
            <li>Extraire des informations à des fins commerciales légitimes</li>
            <li>Intégrer les résultats d'analyse dans vos propres workflows et applications</li>
            <li>Utiliser les APIs selon les termes de votre abonnement</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">3.2 Utilisations interdites</h3>
          <p className="mb-4">
            Vous vous engagez à ne pas :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Contenu illégal :</strong> Télécharger ou analyser du contenu illégal, diffamatoire, frauduleux ou violant les droits d'autrui</li>
            <li><strong>Contenu sensible :</strong> Traiter des données personnelles sensibles sans autorisation appropriée</li>
            <li><strong>Propriété intellectuelle :</strong> Violer les droits de propriété intellectuelle de tiers</li>
            <li><strong>Sécurité :</strong> Tenter de contourner les mesures de sécurité ou d'accéder aux systèmes non autorisés</li>
            <li><strong>Usage abusif :</strong> Faire un usage excessif qui pourrait affecter les performances du Service</li>
            <li><strong>Rétro-ingénierie :</strong> Tenter de reproduire, copier ou créer des services concurrents</li>
            <li><strong>Automatisation abusive :</strong> Utiliser des bots ou scripts pour un usage intensif non autorisé</li>
            <li><strong>Revente :</strong> Revendre l'accès au Service sans autorisation écrite</li>
          </ul>
        </section>

        {/* 4. Abonnements et paiements */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">4. Abonnements et paiements</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">4.1 Plans d'abonnement</h3>
          <p className="mb-4">
            Nous proposons différents plans d'abonnement avec des fonctionnalités et limites variables. Les détails des plans, tarifs et limites sont disponibles sur notre site web et peuvent être modifiés à tout moment.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">4.2 Facturation</h3>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Les frais d'abonnement sont facturés à l'avance sur une base mensuelle ou annuelle</li>
            <li>Les paiements sont traités automatiquement via notre processeur de paiement sécurisé</li>
            <li>Tous les prix sont exprimés en devises locales applicables et incluent les taxes</li>
            <li>Les frais sont non remboursables sauf disposition contraire de ces Conditions</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">4.3 Modifications de tarifs</h3>
          <p className="mb-4">
            Nous nous réservons le droit de modifier nos tarifs à tout moment. Les modifications de prix prendront effet à votre prochain cycle de facturation et vous serez informé au moins 30 jours à l'avance.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">4.4 Suspension pour non-paiement</h3>
          <p className="mb-4">
            En cas de défaut de paiement, nous nous réservons le droit de suspendre votre accès au Service après un préavis de 7 jours. Votre compte sera réactivé une fois le paiement effectué.
          </p>
        </section>

        {/* 5. Propriété intellectuelle */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">5. Propriété intellectuelle</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">5.1 Propriété du Service</h3>
          <p className="mb-4">
            Le Service, incluant mais non limité au logiciel, aux algorithmes d'IA, à l'interface utilisateur, au contenu, aux marques et à tous les droits de propriété intellectuelle associés, appartient à FlexiAnalyse et est protégé par les lois sur la propriété intellectuelle.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">5.2 Licence d'utilisation</h3>
          <p className="mb-4">
            Nous vous accordons une licence limitée, non exclusive, non transférable et révocable pour utiliser le Service conformément à ces Conditions pendant la durée de votre abonnement.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">5.3 Vos contenus</h3>
          <p className="mb-4">
            Vous conservez tous vos droits sur les documents que vous téléchargez. En utilisant le Service, vous nous accordez une licence temporaire pour traiter vos documents uniquement dans le but de fournir le Service. Cette licence expire lorsque vos documents sont supprimés de nos systèmes.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">5.4 Résultats d'analyse</h3>
          <p className="mb-4">
            Vous possédez les droits sur les résultats d'analyse générés à partir de vos documents. Nous conservons le droit d'utiliser des données agrégées et anonymisées pour améliorer nos services, sans vous identifier.
          </p>
        </section>

        {/* 6. Confidentialité et sécurité */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">6. Confidentialité et sécurité</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">6.1 Protection des données</h3>
          <p className="mb-4">
            Nous nous engageons à protéger vos données conformément à notre Politique de Confidentialité. Vos documents sont traités de manière sécurisée et ne sont pas stockés de manière permanente sauf si vous choisissez explicitement de les sauvegarder.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">6.2 Mesures de sécurité</h3>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Chiffrement des données en transit et au repos</li>
            <li>Authentification sécurisée via Google OAuth</li>
            <li>Surveillance continue des systèmes</li>
            <li>Sauvegardes régulières et sécurisées</li>
            <li>Accès limité aux données par le personnel autorisé</li>
          </ul>
        </section>

        {/* 7. Responsabilités et limitations */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">7. Responsabilités et limitations</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">7.1 Vos responsabilités</h3>
          <ul className="list-disc ml-6 mb-4 space-y-2">
            <li><strong>Contenu :</strong> Vous êtes seul responsable du contenu que vous téléchargez et traitez</li>
            <li><strong>Conformité :</strong> Vous devez vous assurer que votre utilisation respecte toutes les lois applicables</li>
            <li><strong>Sécurité :</strong> Vous êtes responsable de la sécurité de votre compte et de vos informations d'accès</li>
            <li><strong>Validation :</strong> Vous devez valider et vérifier tous les résultats générés par l'IA avant utilisation</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">7.2 Limitations de notre responsabilité</h3>
          <div className="bg-yellow-50 p-4 rounded-lg mb-4">
            <p className="mb-2"><strong>IMPORTANT :</strong> Les résultats générés par notre IA sont fournis "en l'état" et ne constituent pas des conseils professionnels.</p>
            <ul className="list-disc ml-6 space-y-1">
              <li>Les résultats peuvent contenir des erreurs ou être incomplets</li>
              <li>Nous ne garantissons pas l'exactitude, la fiabilité ou l'exhaustivité des analyses</li>
              <li>Vous devez toujours vérifier et valider les résultats avant de prendre des décisions</li>
            </ul>
          </div>

          <h3 className="text-xl font-medium mt-6 mb-3">7.3 Exclusion de garanties</h3>
          <p className="mb-4">
            LE SERVICE EST FOURNI "TEL QUEL" ET "TEL QUE DISPONIBLE". NOUS DÉCLINONS TOUTE GARANTIE, EXPRESSE OU IMPLICITE, Y COMPRIS LES GARANTIES DE QUALITÉ MARCHANDE, D'ADÉQUATION À UN USAGE PARTICULIER ET DE NON-CONTREFAÇON.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">7.4 Limitation des dommages</h3>
          <p className="mb-4">
            EN AUCUN CAS NOUS NE SERONS RESPONSABLES DE DOMMAGES INDIRECTS, SPÉCIAUX, ACCESSOIRES OU CONSÉCUTIFS, Y COMPRIS LA PERTE DE PROFITS, DE DONNÉES OU D'USAGE, MÊME SI NOUS AVONS ÉTÉ INFORMÉS DE LA POSSIBILITÉ DE TELS DOMMAGES.
          </p>
        </section>

        {/* 8. Disponibilité du service */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">8. Disponibilité du service</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">8.1 Niveau de service</h3>
          <p className="mb-4">
            Nous nous efforçons de maintenir une disponibilité élevée du Service, mais nous ne garantissons pas un service ininterrompu. Le Service peut être temporairement indisponible pour maintenance, mises à jour ou en cas de circonstances indépendantes de notre volonté.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">8.2 Maintenance programmée</h3>
          <p className="mb-4">
            Nous nous réservons le droit d'effectuer des maintenances programmées qui peuvent temporairement interrompre le Service. Nous nous efforcerons de vous informer à l'avance de ces interruptions.
          </p>
        </section>

        {/* 9. Résiliation */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">9. Résiliation</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">9.1 Résiliation par vous</h3>
          <p className="mb-4">
            Vous pouvez résilier votre abonnement à tout moment via les paramètres de votre compte. La résiliation prendra effet à la fin de votre période de facturation en cours, sans remboursement des frais déjà payés.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">9.2 Résiliation par nous</h3>
          <p className="mb-4">
            Nous pouvons résilier votre accès au Service immédiatement et sans préavis si :
          </p>
          <ul className="list-disc ml-6 mb-4 space-y-1">
            <li>Vous violez ces Conditions</li>
            <li>Votre utilisation nuit au Service ou à d'autres utilisateurs</li>
            <li>Nous soupçonnons une activité frauduleuse</li>
            <li>Requis par la loi ou une autorité compétente</li>
          </ul>

          <h3 className="text-xl font-medium mt-6 mb-3">9.3 Effets de la résiliation</h3>
          <p className="mb-4">
            Après résiliation, votre accès au Service cessera immédiatement et vos données seront supprimées conformément à notre Politique de Confidentialité, sauf obligation légale contraire.
          </p>
        </section>

        {/* 10. Force majeure */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">10. Force majeure</h2>
          <p className="mb-4">
            Nous ne serons pas responsables de tout retard ou défaut d'exécution résultant de causes indépendantes de notre contrôle raisonnable, notamment : catastrophes naturelles, guerre, terrorisme, émeutes, embargos, actes d'autorités civiles ou militaires, incendie, inondations, accidents, grèves ou pénuries de moyens de transport, installations ou matières premières.
          </p>
        </section>

        {/* 11. Modifications des conditions */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">11. Modifications des conditions</h2>
          <p className="mb-4">
            Nous nous réservons le droit de modifier ces Conditions à tout moment. Les modifications importantes seront communiquées par email ou via une notification sur la plateforme au moins 30 jours avant leur entrée en vigueur.
          </p>
          <p className="mb-4">
            Votre utilisation continue du Service après l'entrée en vigueur des modifications constitue votre acceptation des nouvelles Conditions. Si vous n'acceptez pas les modifications, vous devez cesser d'utiliser le Service.
          </p>
        </section>

        {/* 12. Droit applicable et juridiction */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">12. Droit applicable et juridiction</h2>
          <p className="mb-4">
            Ces Conditions sont régies par le droit [français/canadien - à préciser selon votre juridiction]. Tout litige relatif à ces Conditions ou au Service sera soumis à la juridiction exclusive des tribunaux de [votre ville/région].
          </p>
        </section>

        {/* 13. Dispositions diverses */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">13. Dispositions diverses</h2>
          
          <h3 className="text-xl font-medium mt-6 mb-3">13.1 Intégralité de l'accord</h3>
          <p className="mb-4">
            Ces Conditions, ainsi que notre Politique de Confidentialité, constituent l'intégralité de l'accord entre vous et nous concernant le Service.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">13.2 Divisibilité</h3>
          <p className="mb-4">
            Si une disposition de ces Conditions est jugée invalide ou inapplicable, les autres dispositions resteront en vigueur.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">13.3 Renonciation</h3>
          <p className="mb-4">
            Notre défaut d'exercer ou de faire appliquer un droit ou une disposition de ces Conditions ne constitue pas une renonciation à ce droit ou à cette disposition.
          </p>

          <h3 className="text-xl font-medium mt-6 mb-3">13.4 Cession</h3>
          <p className="mb-4">
            Vous ne pouvez pas céder vos droits en vertu de ces Conditions sans notre consentement écrit préalable. Nous pouvons céder nos droits à tout moment sans restriction.
          </p>
        </section>

        {/* 14. Contact */}
        <section>
          <h2 className="text-2xl font-semibold mt-8 mb-4">14. Contact</h2>
          <p className="mb-4">
            Pour toute question concernant ces Conditions d'utilisation, veuillez nous contacter :
          </p>
          <div className="bg-gray-50 p-4 rounded-lg">
            <p><strong>Email :</strong> <a href="mailto:legal@flexianalyse.com" className="text-blue-600 hover:underline">infos@flexianalyse.com</a></p>
            <p><strong>Support :</strong> <a href="mailto:contact@flexianalyse.com" className="text-blue-600 hover:underline">infos@flexianalyse.com</a></p>
            <p><strong>Adresse :</strong> FlexiAnalyse, 8050 Rue saint Jacques, Canada</p>
            <p><strong>Téléphone :</strong> 647-321-9396</p>
          </div>
        </section>
      </div>

      <div className="mt-12 pt-6 border-t border-gray-200">
        <p className="text-sm text-gray-600">
          Ces conditions d'utilisation ont été mises à jour le 24 septembre 2025 pour refléter 
          les fonctionnalités actuelles du service et les exigences légales applicables.
        </p>
      </div>
    </div>
  );
};

export default TermsOfUse;