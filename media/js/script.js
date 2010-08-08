function linebreaks(str) {
    return str.replace(/\n/g, "<br />");
}
function fix_amps(str) {
    // Fix &amp;quot; nonsense.
    while (str.indexOf("&amp;") != -1) {
        str = str.replace(/&amp;/g, "&");
    }
    str = str.replace(/&(?!(#[a-z\d]+|\w+);)/gi, "&amp;");
    return str;
}
function linkify(text, phrases) {
    // Get character ranges over which links are valid.
    var flat = text.replace(/\n/g, " ").toUpperCase();
    var beginnings = {}; // beginning position: [ rid, rid, rid ]
    var endings = {};    // ending position: [ rid, rid, rid ]
    for (var phrase in phrases) {
        var start = flat.indexOf(phrase);
        var end = start + phrase.length;
        if (beginnings[start] == undefined) {
            beginnings[start] = [];
        }
        // add all links to this beginning position
        beginnings[start] = beginnings[start].concat(phrases[phrase]);
        if (endings[end] == undefined) {
            endings[end] = [];
        }
        endings[end] = endings[end].concat(phrases[phrase]);
    }
    // Split the text into spans for the ranges.
    var out = [];
    var within = []; // list of rid's we are currently in range of
    for (var i = 0; i < text.length; i++) {
        if (endings[i] || beginnings[i]) {
            if (within.length > 0) {
                out.push("</span>");
            }
            if (endings[i]) {
                // remove everything in 'within' that is in 'endings[i]' 
                for (var j = 0; j < endings[i].length; j++) {
                    var pos = $.inArray(endings[i][j], within);
                    if (pos != -1) {
                        within.splice(pos, 1);
                    }
                }
            }
            if (beginnings[i]) {
                for (var j = 0; j < beginnings[i].length; j++) {
                    if ($.inArray(beginnings[i][j], within) == -1) {
                        within.push(beginnings[i][j]);
                    }
                }
            }
            if (within.length > 0) {
                out.push("<span class='links ");
                out.push($.map(within, function(w) { return "key" + w }).join(" "));
                out.push(" numlinks" + Math.min(10, within.length));
                out.push("'>");
            }
        }
        out.push(text.substring(i, i+1));
    }
    return [acronyms(out.join(""))];
}
function displayText(tokens, div, popup_url, loading_text) {
    for (var i = 0; i < tokens.length; i++) {
        $(div).append(linebreaks(fix_amps(tokens[i])));
    }
    // Callback for links
    $(div).parent().bind("click", function() { 
        $(".popup").remove() 
        clickout = false;
    });
    $(div).find(".links").bind("click", function(event) {
        event.stopPropagation();
        $(".popup").remove();
        var content = $(document.createElement("div")).attr("class", "content").html(
            loading_text
        );
        
        // get inner text.  Must un-expand acronyms first.
        var acronymChecked = $('#toggleAcronyms').is(":checked");
        if (acronymChecked) {
            toggleAcronyms(false);
        }
        var clicked = $(this).text().toUpperCase().replace(/\s+$/g, '').replace(/^\s+/g, '');
        if (acronymChecked) {
            toggleAcronyms(true);
        }

        // Create popup div.
        var pop = $(document.createElement("div")).attr("class", "popup").append(
                $(document.createElement("a")).attr("class", "close")
                    .html("close")
                    .bind("click", function() { $(this).parent().remove(); })
            ).append(content);
        var offset = $(this).offset();
        var parent = $(this).parent(); 
        var parOffset = parent.offset();
        var newOffset = {
            'left': parOffset.left + 10,
            'top': offset.top + 15
        };
        pop.hide();
        $("body").append(pop);
        pop.fadeIn();
        pop.width($(this).parent().width() - 30);
        pop.offset(newOffset);
        pop.offset(newOffset); // chrome/safari bug; have to do this twice
        var ids = [];
        $.each(this.className.split(' '), function(i, classname) {
            var match = /key(\d+)/.exec(classname);
            if (match) {
                ids.push(parseInt(match[1]));
            }
        });
        
        // Find text to highlight.
        var texts = [];
        for (var i = 0; i < ids.length; i++) {
            var bestText = "";
            var possibleTexts = linkPhrases[ids[i]];
            for (var j = 0; j < possibleTexts.length; j++) {
                var ptext = possibleTexts[j].replace(/\s+$/g, '').replace(/^\s+/g, '');
                if (ptext.length > bestText.length && ptext.indexOf(clicked) != -1) {
                    bestText = ptext;
                }
            }
            texts.push(escape(bestText));
        }

        $.ajax({
            type: "GET",
            url: popup_url,
            data: { 
                'rids': ids.join(","), 
                'clicked': this.innerHTML, 
                'texts': texts.join(",")
            },
            success: function(html) {
                content.html(html);
            },
            error: function() {
                content.html("Error communicating with server.");
            }
        });

    });
}
var ACRONYMS = [
    [/\b(\d+IN)\b/g, "Infantry group"],
    [/\b(\d+US)\b/g, "Number of US personnel"],
    [/\b(\d+V)\b/g, "Vehicles"],
    [/\b((\d\d)(\d\d)L)\b/gi, "$2:$3 Local time"],
    [/\b((\d\d)(\d\d)Z)/gi, "$2:$3 GMT"],
    [/\b(42 CDO RM)\b/g, "42 Commando Royal Marines"],
    [/\b(508 STB)\b/g, "508th special troops battalion"],
    [/\b(81)\b/g, "81mm mortar round"],
    [/\b(9-liner)\b/g, "9 Line MEDEVAC Request"],
    [/\b(A\/C)\b/g, "aircraft"],
    [/\b(AAF)\b/g, "Anti-Afghan forces"],
    [/\b(ABP)\b/g, "Afghan Border Police"],
    [/\b(AC-130)\b/g, "Gunship adapted from Hercules"],
    [/\b(ACK)\b/g, "Acknowledge"],
    [/\b(ACMs?)\b/g, "Anti-Coalition Militia"],
    [/\b(AGL)\b/g, "Above Ground Level [Altitude]"],
    [/\b(AFG)\b/g, "Afghans"],
    [/\b(AH)\b/g, "Attack helicopter"],
    [/\b(AIHRC)\b/g, "Afghan Independent Human Right Commission"],
    [/\b(AK-47)\b/g, "Assault rifle"],
    [/\b(AMF)\b/g, "Afghan Military Forces"],
    [/\b(ANA)\b/g, "Afghan National Army"],
    [/\b(ANAP)\b/g, "Afghan National Auxiliary Police"],
    [/\b(ANBP)\b/g, "Afghan National Border Police"],
    [/\b(ANP)\b/g, "Afghan National Police"],
    [/\b(ANSF)\b/g, "Afghan National Security Forces"],
    [/\b(AO)\b/g, "Area of operation"],
    [/\b(AQ)\b/g, "Al Qaida"],
    [/\b(ARSIC)\b/g, "Afghan Regional Security Integrated Command"],
    [/\b(ASE)\b/g, "Aircraft Survivability Equipment"],
    [/\b(ASG)\b/g, "Area Support Group"],
    [/\b(ASV)\b/g, "Armoured Security Vehicle"],
    [/\b(ATT)\b/gi, "At this time"],
    [/\b(ATTK)\b/g, "Attack"],
    [/\b(AUP)\b/g, "Afghan Uniform Police"],
    [/\b(AUS)\b/g, "Australian"],
    [/\b(B-HUTS)\b/g, "Semi-permanent wooden structure (used in place of tents)"],
    [/\b(BAF)\b/g, "Bagram Air Field"],
    [/\b(BCT)\b/g, "Brigade combat team (US)"],
    [/\b(BDA)\b/g, "Battle Damage Assessment"],
    [/\b(BDE)\b/g, "Brigade"],
    [/\b(Beaten zone)\b/g, "Area where spread of rounds fired"],
    [/\b(BFT)\b/g, "Blue Force Tracking [identifying friendly forces in area]"],
    [/\b(BG)\b/g, "Brigadier General"],
    [/\b(Blue forces)\b/g, "Nato/ISAF forces"],
    [/\b(Blue on Blue)\b/g, "Friendly fire"],
    [/\b(BN)\b/g, "Battalion"],
    [/\b(BP)\b/g, "Blood Pressure"],
    [/\b(BPT)\b/g, "Be[ing] prepared to"],
    [/\b(BRF)\b/g, "Brigade Reconnaissance Force"],
    [/\b(BSN)\b/g, "(Camp) Bastion"],
    [/\b(BSSM)\b/g, "Border Security Subcommittee Meeting"],
    [/\b(BTG)\b/g, "Basic Target Graphic"],
    [/\b(BTIF)\b/g, "Bagram Theatre Internment Facility"],
    [/\b(BTL)\b/g, "Battalion"],
    [/\b(buzz saw)\b/g, "Signalling method by waving light stick in circle"],
    [/\b(C\/\/NF)\b/g, "Confidential, No Foreign Nationals"],
    [/\b(C\/S)\b/g, "Call Sign"],
    [/\b(CA)\b/g, "Civil Affairs"],
    [/\b(CAN)\b/g, "Canadian"],
    [/\b(CAS)\b/g, "Close Air Support"],
    [/\b(CAT A)\b/g, "Category A patient"],
    [/\b(CAT B)\b/g, "Category B patient"],
    [/\b(CAT C)\b/g, "Category C patient [priority]"],
    [/\b(CCA)\b/g, "Carrier-Controlled Approach"],
    [/\b(CCIR)\b/g, "Commander's Critical Information Requirements"],
    [/\b(CD)\b/g, "Command"],
    [/\b(CDN)\b/g, "Canadian"],
    [/\b(CDR)\b/g, "Commander"],
    [/\b(CF)\b/g, "Coalition Forces"],
    [/\b(CG)\b/g, "Coldstream Guards"],
    [/\b(CGBG)\b/g, "Coldstream Guards Battle Group"],
    [/\b(cgbg 1 coy)\b/g, "1 Company, Coldstream Guards battle group"],
    [/\b(CHOPS)\b/g, "Chief of Operations"],
    [/\b(CIV)\b/g, "Civilian"],
    [/\b(CIVCAS)\b/g, "Civilian casualties"],
    [/\b(CJ2)\b/g, "US intelligence and Security Command, Afghanistan"],
    [/\b(CJ3)\b/g, "Joint Special Ops"],
    [/\b(CJSOTF)/g, "Combined Joint Special Operations Task Force"],
    [/\b(CJTF)/g, "Combined Joint Task Force"],
    [/\b(CJTF-82)\b/g, "Combined Joint Task Force-82 [HQ of US Forces in ISAF and Regional Command East, March 2007-April 2008]"],
    [/\b(CLP)\b/g, "Combat Logistics Patrol [supply convoy]"],
    [/\b(CMWS)\b/g, "Common Missile Warning System"],
    [/\b(CO)\b/g, "Commanding Officer"],
    [/\b(CoP)\b/g, "Chief of Police"],
    [/\b(COP)\b/g, "Combat outpost"],
    [/\b(Coy)\b/gi, "Company"],
    [/\b(CP)\b/g, "Check Point"],
    [/\b(cpt)\b/gi, "Captain"],
    [/\b(Csh)\b/gi, "Combat Support Hospital"],
    [/\b(CTC)\b/g, "Counterterrorist Center [?]"],
    [/\b(CWIED)\b/g, "Command Wire Improvised Explosive Device"],
    [/\b(DBC)\b/g, "Database Code"],
    [/\b(DC)\b/g, "District Centre"],
    [/\b(DF)\b/g, "Direct Fire"],
    [/\b(DISC SEPARATION)\b/gi, "Distance between aircraft [units of rotor diameter]"],
    [/\b(DOI)\b/g, "Date of Incident"],
    [/\b(DoS)\b/g, "Department of State"],
    [/\b(DOW)\b/g, "Died of Wounds"],
    [/\b(DSHKA)\b/g, "Soviet-origin Heavy Machine Gun"],
    [/\b(ECP)\b/g, "Entry Control Point"],
    [/\b(EWIA)\b/g, "Enemy Wounded in Action"],
    [/\b(EKIA)\b/g, "Enemy Killed in Action"],
    //[/\b(Element)\b/gi, "task force part"],
    [/\b(EN(?! ROUTE))\b/gi, "Enemy"],
    [/\b(ENG BDE)\b/g, "Engineer Brigade"],
    [/\b(EOC)\b/g, "Emergency Operation Centre"],
    [/\b(EOD)\b/g, "Explosive Ordnance Disposal [bomb defuser]"],
    [/\b(EOF)\b/gi, "Escalation of Force"],
    [/\b(ETT)\b/g, "Embedded Training Team"],
    [/\b(evac)\b/gi, "Evacuation"],
    [/\b(EVACD)\b/gi, "Evacuated"],
    [/\b(F-15)\b/g, "F-15 Fighter/bomber"],
    [/\b(FB)\b/g, "Forward Base"],
    [/\b(FF)\b/g, "Friendly Forces"],
    [/\b(FFIR)\b/g, "Friendly Forces Information Requirement"],
    [/\b(FIR)\b/g, "First Impressions Report"],
    [/\b(FMC)\b/g, "Fully Mission Capable"],
    [/\b(FO)\b/g, "Forward Observer"],
    [/\b(FOB)\b/g, "Forward Operating Base"],
    [/\b(FP)\b/g, "Firing Point"],
    [/\b(FPS)\b/g, "Facility protection service"],
    [/\b(FRA BG)\b/g, "French battle group"],
    [/\b(FSB)\b/g, "Forward Support Base"],
    [/\b(FW)\b/g, "Fixed-wing"],
    [/\b(GBU)\b/g, "Guided Bomb Unit"],
    [/\b(GBU-12)\b/g, "500lb laser-guided 'smart bomb'"],
    [/\b(GBU-31)\b/g, "2,000lb smart bomb"],
    [/\b(GBU-38)\b/g, "GPS/laser guided 500lb 'smart' bomb"],
    [/\b(GCTF)\b/g, "Global Counter Terrorism Forces"],
    [/\b(GEN)\b/g, "General"],
    [/\b(GHZ)\b/g, "Ghazni"],
    [/\b(GIRoA)\b/g, "Government of the Islamic Republic of Afghanistan"],
    [/\b(GMLRS)\b/g, "Multiple rocket launcher"],
    [/\b(Green on green)\b/g, "Fighting between Afghan forces"],
    [/\b(GSW)\b/g, "Gunshot wound"],
    [/\b(GT R2RR)\b/g, "Canadian troops: tactical group:2nd bn 22nd royal regiment"],
    [/\b(helos)\b/g, "Helicopters"],
    [/\b(HA)\b/g, "Humanitarian Assistance"],
    [/\b(HHB)\b/g, "Headquarters and Headquarters Battalion"],
    [/\b(HIMARS)\b/g, "GPS-guided multiple rocket system [mounted on mobile truck - carries GMLRS qv]"],
    [/\b(HLZ)\b/g, "helicopter landing zone"],
    [/\b(HMG)\b/g, "UK government (HM Government)"],
    [/\b(HMLA-169)\b/g, "US Marines light attack helicopter sqadron"],
    [/\b(HRT)\b/g, "Hostage Rescue Team"],
    [/\b(HVI)\b/g, "High-value Individual"],
    [/\b(HWY)\b/g, "Highway"],
    [/\b(IAW)\b/g, "In accordance with"],
    [/\b(ICOM)\b/g, "Radio"],
    [/\b(IDF)\b/g, "Indirect Fire"],
    [/\b(IED)\b/g, "Improvised Explosive Device"],
    [/\b(Illum)\b/g, "Illumination mortar, fired to provide light"],
    [/\b(INFIL)\b/g, "Infiltrate"],
    [/\b(INS)\b/g, "Insurgents"],
    [/\b(INTSUM)\b/g, "Intelligence summary"],
    [/\b(IO)\b/g, "Information operations"],
    [/\b(IOT)\b/g, "In order to"],
    [/\b(IR)\b/g, "Incident Report"],
    [/\b(ir)\b/g, "infrared"],
    [/\b(IR STROBE)\b/g, "Infrared Strobe"],
    [/\b(IRoA)\b/g, "Islamic Republic of Afghanistan"],
    [/\b(IRCCM)\b/g, "Infra Red Counter-Countermeasures"],
    [/\b(IRT)\b/g, "Incident Response Team?"],
    [/\b(ISAF)\b/g, "International Security Assistance Force"],
    [/\b(ISN)\b/g, "Internment [or Insurgent] serial Number"],
    [/\b(ISO)\b/g, "In support of"],
    [/\b(ISR)\b/g, "Intelligence, surveillance and reconnaissance"],
    [/\b(IVO)\b/g, "In the vicinity of"],
    [/\b(J COY 42 CDO)\b/g, "J company 42 Commando Royal Marines"],
    [/\b(JAF)\b/g, "Jalalabad Air Field"],
    [/\b(JAG)\b/g, "Judge Advocate General (Army legal team)"],
    [/\b(JBAD)\b/g, "Jalalabad"],
    [/\b(JDAM)\b/g, "Joint Direct Attack Munition"],
    [/\b(JDCC)\b/g, "Joint District Coordination Center"],
    [/\b(JDOC)\b/g, "Joint Defense Operations Center"],
    [/\b(JEL)\b/g, "Joint Effects List [hit list]"],
    [/\b(Jingle trucks)\b/g, "Brightly decorated trucks covered in bells [common across central Asia]"],
    [/\b(JOC)\b/g, "Joint Ops Centre"],
    [/\b(JPEL)\b/g, "Joint Prioritised Effects List [hit list]"],
    [/\b(JTAC)\b/g, "Joint terminal air controller"],
    [/\b(JUGROOM)\b/g, "Fort, Garmsir, Afghanistan"],
    [/\b(KAF)\b/g, "Kandahar Air Field"],
    [/\b(KAIA)\b/g, "Kabul international airport"],
    [/\b(KDZ)\b/g, "Kunduz"],
    [/\b(KIA)\b/g, "Killed in Action"],
    [/\b(KIAS)\b/g, "Knots Indicated Air Speed"],
    [/\b(KJI)\b/g, "Kajaki"],
    [/\b(KLE(s?))\b/g, "Key Leader Engagement$2"],
    [/\b(KMTC)\b/g, "Kabul Military Training Cetnre"],
    [/\b(KPRT)\b/g, "Kandahar Provincial Reconstruction Team"],
    [/\b(L:)\b/g, "Location (in relation to S, A, L, T)"],
    [/\b(LEP)\b/g, "Law Enforcement Professionals"],
    [/\b(Line 1)\b/g, "Location of the pick-up site."],
    [/\b(Line 2)\b/g, "Radio frequency, call sign, and suffix."],
    [/\b(Line 3)\b/g, "Number of patients by precedence: A to E with A being most urgent"],
    [/\b(Line 4)\b/g, "Special equipment required"],
    [/\b(Litter)\b/g, "Medical Stretcher"],
    [/\b(LKG)\b/g, "Lashkar Ghar"],
    [/\b((\d+)xLN)\b/g, "$2 Local Nationals"],
    [/\b(L\/?N)\b/g, "Local National"],
    [/\b(LNs)\b/gi, "Local Nationals"],
    [/\b(LNO)\b/g, "Liaison Officer"],
    [/\b(LTC)\b/g, "Lieutenant Colonel"],
    [/\b(Luna)\b/g, "German drone"],
    [/\b(LZ)\b/g, "Landing Zone"],
    [/\b(m240b)\b/g, "Type of machine gun"],
    [/\b(M249)\b/g, "light machine gun"],
    [/\b(M4)\b/g, "Type of gun"],
    [/\b(M-4)\b/g, "Type of gun"],
    [/\b(MAJ)\b/g, "Major"],
    [/\b(MANPAD)\b/g, "Man-Portable Air-Defense System"],
    [/\b(MAR)\b/g, "Marine"],
    [/\b(MEDE?VACD?)\b/gi, "Medical Evacuation"],
    [/\b(MED OPS)\b/g, "Medical Operations"],
    [/\b(MED TM)\b/g, "Medical Team"],
    [/\b(MEY PRT)\b/g, "Meymaneh provincial reconstruction team"],
    [/\b(MG)\b/g, "Machine Gun"],
    [/\b(MHL)\b/g, "Mehtar Lam"],
    [/\b(MM)\b/g, "Military Message"],
    [/\b(MOD)\b/g, "Ministry of Defence"],
    [/\b(MOI)\b/g, "Afghanistan's Ministry of Interior"],
    [/\b(MP)\b/g, "Military Police"],
    [/\b(MS)\b/g, "Military support"],
    [/\b(MSN)\b/g, "Nurse (with a masters)"],
    [/\b(Msr)\b/g, "Main Supply Route"],
    [/\b(MTF)\b/g, "More to follow"],
    [/\b(MTT)\b/g, "Military Training Team"],
    [/\b(MWE)\b/g, "Men, Weapons and Equipment"],
    [/\b(MWS)\b/g, "Missile Warning System"],
    [/\b(N\/I C)\b/g, "Nato/ISAF Confidential"],
    [/\b(NAI)\b/g, "Named areas of interest"],
    [/\b(NC)\b/g, "non-combatant"],
    [/\b(NCO)\b/g, "Non-commissioned officer"],
    [/\b(NDS)\b/g, "Afghan intelligence [national directorate of security]"],
    [/\b(NFI)\b/g, "No Further Information"],
    [/\b(NFTR)\b/g, "Nothing Further to Report"],
    [/\b(NM)\b/g, "Nautical Miles"],
    [/\b(NMC)\b/g, "Non mission-capable"],
    [/\b(NOFORN)\b/g, "No foreigners [secrecy classification]"],
    [/\b(NSTR)\b/g, "Nothing significant to report"],
    [/\b(OBJ)\b/g, "Objective"],
    [/\b(OC)\b/g, "Outcome"],
    [/\b(OCC- P)\b/g, "Operational Command Centre - Provincial"],
    [/\b(OCCD)\b/g, "Operational Coordination Center District"],
    [/\b(ODA)\b/g, "Operational Detachment (Alpha) - special forces"],
    [/\b(OGA)\b/g, "Other Government Agency (usually CIA)"],
    [/\b(OIC)\b/g, "Officer in charge"],
    [/\b(OMF)\b/g, "Opposing Militant Forces"],
    [/\b(Op)\b/g, "Operation"],
    [/\b(OP)\b/g, "Observation Post"],
    [/\b(OP grid)\b/g, "Operation/Observation post map coordinates"],
    [/\b(OPSUM)\b/g, "Operations Summary"],
    [/\b(ORSA)\b/g, "operations research and systems analysis"],
    [/\b(PA)\b/g, "Physician Assistant"],
    [/\b(PAK)\b/g, "Pakistan"],
    [/\b(PAKMIL)\b/g, "Pakistan military"],
    [/\b(PAO)\b/g, "Public Affairs Officer"],
    [/\b(PAX)\b/g, "Passengers/People"],
    [/\b(PB)\b/g, "Patrol Base"],
    [/\b(PBG)\b/g, "Polish battle group"],
    [/\b(PEF)\b/g, "poppy eradication force [afghan police]"],
    [/\b(PEN)\b/g, "Penich (outpost)"],
    [/\b(PHQ)\b/g, "Police headquarters (in reference to ANP)"],
    [/\b(PID)\b/g, "Positive I.D."],
    [/\b(PKM)\b/g, "Russian-made machine gun"],
    [/\b(PL)\b/g, "Platoon"],
    [/\b(PLT)\b/g, "Platoon"],
    [/\b(PLT SJT)\b/g, "Platoon Seargant"],
    [/\b(PMT)\b/g, "Police Mentor Team"],
    [/\b(PoA)\b/g, "President of Afghanistan"],
    [/\b(poc)\b/g, "Point of Contact"],
    [/\b(POI)\b/g, "Point of Impact"],
    [/\b(POO)\b/g, "Point of Origin"],
    [/\b(PRED)\b/g, "Predator Drone"],
    [/\b(PRO COY)\b/g, "Protection Company"],
    [/\b(PRT)\b/g, "Provincial Reconstruction Team"],
    [/\b(PRT CDR)\b/g, "Provincial Reconstruction Team Commander"],
    [/\b(PSO)\b/g, "Post Security Officer"],
    [/\b(PT)\b/g, "Patient"],
    [/\b(PTS)\b/g, "Peace Through Strength (PTS) reconciliation process"],
    [/\b(PZ)\b/g, "Pickup Zone"],
    [/\b(QRF)\b/g, "Quick Response Force"],
    [/\b(QA\/QC)\b/g, "Quality Assurance/Quality Control"],
    [/\b(RB)\b/g, "Road block"],
    [/\b(RC \(N\))\b/g, "Regional Command North"],
    [/\b(RC CENTRAL)\b/g, "Regional Command Central"],
    [/\b(RC\(E\))\b/g, "Regional Command East"],
    [/\b(RC East)\b/g, "Regional Command East"],
    [/\b(RC\(W\))\b/g, "Regional Command West"],
    [/\b(RC=S)\b/g, "Regional Command South"],
    [/\b(RC\(S\))\b/g, "Regional Command South"],
    [/\b(RCAG)\b/g, "Regional Corps Assistance Group"],
    [/\b(RCC)\b/g, "Regional Command Capital"],
    [/\b(RC\(C\))\b/g, "Regional Command Capital"],
    [/\b(RCIED)\b/g, "Remote Control Improvised Explosive Device"],
    [/\b(RCP)\b/g, "Route clearance Patrol"],
    [/\b(rds)\b/g, "Rounds"],
    [/\b(RDS)\b/g, "Rounds"],
    [/\b(rfs)\b/g, "Resident Field Squadron"],
    [/\b(RG)\b/g, "US armoured vehicle"],
    [/\b(RGR)\b/g, "Royal Gurkha rifles"],
    [/\b(ROE)\b/g, "Rules of engagement"],
    [/\b(RON)\b/g, "Remain Overnight"],
    [/\b(Role 3)\b/g, "Surgical facility"],
    [/\b(RPG)\b/g, "Rocket propelled grenade"],
    [/\b(RPGs)\b/g, "Rocket propelled grenades"],
    [/\b(RPK)\b/g, "Light machine gun, Kalashnikov (Ruchnoi Pulemyot Kalashnikova)"],
    [/\b(RPT)\b/g, "Report"],
    [/\b(RTB)\b/g, "Return to base"],
    [/\b(RTE)\b/g, "Route"],
    [/\b(RTF)\b/g, "Reconstruction Task Force [Australian at TF Uruzgan]"],
    [/\b(S-2)\b/g, "Intelligence staff officer"],
    [/\b(S-5)\b/g, "Staff member responsible for civil-military operations"],
    [/\b(SALUTE)\b/g, "Size/Activity/Location/Unit/Time/Equipment"],
    [/\b(SALUTER)\b/g, "Size/Activity/Location/Unit/Time/Equipment/Result"],
    [/( S[-:])/g, " Size: "],
    [/( A[-:])/g, " Activity: "],
    [/( L[-:])/g, " Location: "],
    [/( T[-:])/g, " Time: "],
    [/( U[-:])/g, " Unit: "],
    [/( E[-:])/g, " Equipment: "],
    [/( R[-:])/g, " Result: "],
    [/\b(S\/\/REL)\b/g, "Secret or Selective release?"],
    [/\b(SAF)\b/g, "Small arms fire"],
    [/\b(Safire)\b/gi, "Small arms fire/Surface-to-Air Fire"],
    [/\b(SAMBUSH)\b/gi, "Surface-to-Air Missle Ambush"],
    [/\b(SAW)\b/g, "Squad Automatic Weapon [ machine gun]"],
    [/\b(SC-26)\b/g, "Scorpion 26 - US special forces unit in Helmand"],
    [/\b(SCIDA)\b/g, "Site Configuration and Installation Design Authority?"],
    [/\b(SEWOC)\b/g, "Sigint Electronic Warfare Operational Centre"],
    [/\b(SFG)\b/g, "special forces group"],
    [/\b(Shura)\b/g, "Meeting of tribal elders and Afghan leaders"],
    [/\b(SIED)\b/g, "Suicide IED"],
    [/\b(SIGACTS?)\b/g, "Significant activity"],
    [/\b(SIR)\b/g, "Serious Incident Report"],
    [/\b(sof)\b/g, "Special ops force"],
    [/\b(SOG)\b/g, "Special ops group"],
    [/\b(Solatia)\b/g, "Payments to civilian victims of US attacks (or their families)"],
    [/\b(SOP)\b/g, "Standard Operating Procedure"],
    [/\b(SOTF)\b/g, "Special Operations Task Force"],
    [/\b(SOTG)\b/g, "Special ops taskgroup"],
    [/\b(SPC)\b/g, "Specialist"],
    [/\b(SQ[DN])\b/gi, "Squadron"],
    [/\b(Squirter)\b/g, "Someone running for cover"],
    [/\b(SSE)\b/g, "Sensitive Site Exploitation"],
    [/\b(SVBIED)\b/g, "Suicide Vehicle-Borne Improvised Explosive Device"],
    [/\b(SWO)\b/g, "Surface Warfare Officer"],
    [/\b(SWT)\b/g, "Scout Weapons Team"],
    [/\b(TB)\b/g, "Taliban"],
    [/\b(TBC)\b/g, "To be confirmed"],
    [/\b(TBD)\b/g, "To be decided"],
    [/\b(TCP)\b/g, "Traffic control point"],
    [/\b(TERP)\b/g, "Interpreter"],
    [/\b(TF)\b/g, "Task force"],
    [/\b(TF373)\b/g, "Task Force 373 [special ops]"],
    [/\b(TFK)\b/g, "Task Force Kandahar"],
    [/\b(TG)\b/g, "Tactical Group"],
    [/\b(TG AREs)\b/g, "Tactical group Ares"],
    [/\b(Thready)\b/g, "Very fine and scarcely perceptible pulse"],
    [/\b(TIC)\b/g, "Troops in Contact"],
    [/\b(Toc)\b/gi, "Tactical Ops Center"],
    [/\b(TTPs?)\b/g, "Tactics, Techniques, and Procedures"],
    [/\b(U\/?I)\b/g, "Unidentified"],
    [/\b(UAH)\b/g, "Up-Armoured Humvee"],
    [/\b(UAV)\b/g, "Unmanned Aerial Vehicle [drone]"],
    [/\b(UH-1N)\b/g, "US Twin Huey transport/communications helicopter"],
    [/\b(UH-60)\b/g, "Black Hawk helicopter"],
    [/\b(UNAMA)\b/g, "United Nations Assistance Mission in Afghanistan"],
    [/\b(UNK)\b/g, "Unknown"],
    [/\b(usfor-a|USFOR-A)\b/g, "United States Forces Afghanistan"],
    [/\b(UXO)\b/g, "unexploded ordnance [or unfired]"],
    [/\b(VBIED)\b/g, "Vehicle-Borne Improvised Explosive Device"],
    [/\b(VCP)\b/g, "Vehicle Check Point"],
    [/\b(vic)\b/g, "vicinity"],
    [/\b(VIC)\b/g, "Vehicle"],
    [/\b(vitals)\b/g, "Vital signs"],
    [/\b(VP)\b/g, "Vulnerable point"],
    [/\b(VPB)\b/g, "Vehicle patrol base"],
    [/\b(VSA)\b/g, "Vital Signs Absent [i.e. dead]"],
    [/\b(w\/d)\b/g, "wheels down"],
    [/\b(w\/u)\b/g, "wheels up"],
    [/\b(White Eagle)\b/g, "Polish Task Force (White Eagle)"],
    [/\b(WIA)\b/g, "Wounded in Action"]
];
function acronyms(string) {
    for (var i = 0; i < ACRONYMS.length; i++) {
        var re = ACRONYMS[i][0];
        var full = ACRONYMS[i][1].replace(/["]/g, "\\\"");
        string = string.replace(re, "<acronym title=\"" + full + "\">$1</acronym>");
    }
    return string;
}
function toggleAcronyms(expand) {
    $("acronym").each(function(index, acronym_element) {
        var a = $(acronym_element);
        var html = a.html();
        var title = a.attr("title");
        var acronym = html.length < title.length ? html : title;
        var definition = html.length > title.length ? html : title;
        if (expand == undefined) {
            expand = $("#toggleAcronyms").is(":checked");
        }
        if (expand) {
            a.attr("title", acronym);
            a.html(definition);
            $(".acronyms-expanded").show();
        } else {
            a.attr("title", definition);
            a.html(acronym);
            $(".acronyms-expanded").hide();
        }
    });
}
