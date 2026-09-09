import React, { createContext, useContext, useState, useEffect } from 'react';

const translations = {
  en: {
    // Header
    'worker.workspace': 'Worker Workspace',
    'profile.strength': 'Profile Strength',
    'verified.worker': 'Verified Worker',
    'pending.verification': 'Pending Verification',
    'rejected.verification': 'Verification Rejected',
    
    // Wallet
    'worker.wallet': 'Worker Wallet',
    'available.withdraw': 'Available to withdraw',
    'jobs.completed': 'Jobs Completed',
    'expected.payout': 'Expected Payout',
    
    // Profile
    'edit.profile': 'Edit Profile',
    'years.experience': 'Years Experience',
    'location.not.set': 'Location not set',
    'skills': 'Skills',
    'no.skills': 'No skills listed',
    'availability': 'Availability',
    'verification': 'Verification',
    'rating': 'Rating',
    
    // Jobs
    'allocated.jobs': 'My Allocated Jobs',
    'jobs.description': 'Cooperative allocated service jobs awaiting your response or execution',
    'no.jobs': 'No Jobs Allocated Currently',
    'no.jobs.sub': 'When cooperative administrators allocate a service request to you, it will appear here.',
    'job.id': 'Job #',
    'awaiting.response': '⏳ Awaiting Response',
    'category': 'Category',
    'location': 'Location',
    'schedule': 'Schedule',
    'customer': 'Customer',
    
    // Actions
    'reject.job': 'Reject Job',
    'accept.job': '✓ Accept Job',
    'start.service': '▶️ Start Service',
    'mark.completed': '✓ Mark Completed',
    'job.completed': '✓ Job Completed',
    
    // New Voice/WhatsApp Actions
    'read.aloud': '🔊 Read Aloud',
    'whatsapp.chat': '💬 WhatsApp',
    'dictate.note': '🎤 Dictate Note',
    'stop.dictation': '⏹️ Stop Dictation',
  },
  hi: {
    // Header
    'worker.workspace': 'कार्यकर्ता कार्यक्षेत्र',
    'profile.strength': 'प्रोफ़ाइल की ताकत',
    'verified.worker': 'सत्यापित कार्यकर्ता',
    'pending.verification': 'सत्यापन लंबित',
    'rejected.verification': 'सत्यापन अस्वीकृत',
    
    // Wallet
    'worker.wallet': 'कार्यकर्ता वॉलेट',
    'available.withdraw': 'निकालने के लिए उपलब्ध',
    'jobs.completed': 'पूरे किए गए कार्य',
    'expected.payout': 'अपेक्षित भुगतान',
    
    // Profile
    'edit.profile': 'प्रोफ़ाइल संपादित करें',
    'years.experience': 'वर्षों का अनुभव',
    'location.not.set': 'स्थान निर्धारित नहीं है',
    'skills': 'कौशल',
    'no.skills': 'कोई कौशल सूचीबद्ध नहीं है',
    'availability': 'उपलब्धता',
    'verification': 'सत्यापन',
    'rating': 'रेटिंग',
    
    // Jobs
    'allocated.jobs': 'मेरे आवंटित कार्य',
    'jobs.description': 'सहकारी आवंटित सेवा कार्य आपकी प्रतिक्रिया या निष्पादन की प्रतीक्षा कर रहे हैं',
    'no.jobs': 'वर्तमान में कोई कार्य आवंटित नहीं है',
    'no.jobs.sub': 'जब सहकारी प्रशासक आपको कोई सेवा अनुरोध आवंटित करते हैं, तो वह यहां दिखाई देगा।',
    'job.id': 'कार्य #',
    'awaiting.response': '⏳ प्रतिक्रिया की प्रतीक्षा में',
    'category': 'श्रेणी',
    'location': 'स्थान',
    'schedule': 'अनुसूची',
    'customer': 'ग्राहक',
    
    // Actions
    'reject.job': 'कार्य अस्वीकार करें',
    'accept.job': '✓ कार्य स्वीकार करें',
    'start.service': '▶️ सेवा प्रारंभ करें',
    'mark.completed': '✓ पूर्ण के रूप में चिह्नित करें',
    'job.completed': '✓ कार्य पूर्ण',
    
    // New Voice/WhatsApp Actions
    'read.aloud': '🔊 जोर से पढ़ें',
    'whatsapp.chat': '💬 व्हाट्सएप',
    'dictate.note': '🎤 वॉयस नोट',
    'stop.dictation': '⏹️ डिक्टेशन रोकें',
  },
  mr: {
    // Header
    'worker.workspace': 'कामगार कार्यक्षेत्र',
    'profile.strength': 'प्रोफाइल ताकद',
    'verified.worker': 'सत्यापित कामगार',
    'pending.verification': 'पडताळणी प्रलंबित',
    'rejected.verification': 'पडताळणी नाकारली',
    
    // Wallet
    'worker.wallet': 'कामगार वॉलेट',
    'available.withdraw': 'काढण्यासाठी उपलब्ध',
    'jobs.completed': 'पूर्ण केलेली कामे',
    'expected.payout': 'अपेक्षित पेमेंट',
    
    // Profile
    'edit.profile': 'प्रोफाइल संपादित करा',
    'years.experience': 'वर्षांचा अनुभव',
    'location.not.set': 'स्थान सेट केलेले नाही',
    'skills': 'कौशल्ये',
    'no.skills': 'कोणतीही कौशल्ये सूचीबद्ध नाहीत',
    'availability': 'उपलब्धता',
    'verification': 'पडताळणी',
    'rating': 'रेटिंग',
    
    // Jobs
    'allocated.jobs': 'माझी वाटप केलेली कामे',
    'jobs.description': 'सहकारी वाटप केलेली सेवा कामे तुमच्या प्रतिसादाची किंवा अंमलबजावणीची वाट पाहत आहेत',
    'no.jobs': 'सध्या कोणतेही काम वाटप केलेले नाही',
    'no.jobs.sub': 'जेव्हा सहकारी प्रशासक तुम्हाला सेवा विनंती वाटप करतात, तेव्हा ती येथे दिसेल.',
    'job.id': 'काम #',
    'awaiting.response': '⏳ प्रतिसादाची प्रतीक्षा',
    'category': 'श्रेणी',
    'location': 'स्थान',
    'schedule': 'वेळापत्रक',
    'customer': 'ग्राहक',
    
    // Actions
    'reject.job': 'काम नाकारा',
    'accept.job': '✓ काम स्वीकारा',
    'start.service': '▶️ सेवा सुरू करा',
    'mark.completed': '✓ पूर्ण म्हणून चिन्हांकित करा',
    'job.completed': '✓ काम पूर्ण',
    
    // New Voice/WhatsApp Actions
    'read.aloud': '🔊 मोठ्याने वाचा',
    'whatsapp.chat': '💬 व्हॉट्सॲप',
    'dictate.note': '🎤 व्हॉइस नोट',
    'stop.dictation': '⏹️ डिक्टेशन थांबवा',
  }
};

const LanguageContext = createContext();

export const LanguageProvider = ({ children }) => {
  const [language, setLanguage] = useState(() => {
    return localStorage.getItem('appLanguage') || 'en';
  });

  useEffect(() => {
    localStorage.setItem('appLanguage', language);
  }, [language]);

  const t = (key) => {
    return translations[language][key] || translations['en'][key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
};

export const useLanguage = () => useContext(LanguageContext);
