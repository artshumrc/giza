# Site display data 
# TODO: Get Primary Image URL (need an image server first)
SITES = """
SELECT Sites.SiteID, SiteName, SiteNumber, SiteSortNumber, HistoricalNotes, 
LegalNotes + ',,' AS BibReferences, LocationNotes, 
Sites.Remarks + ',,' AS Remarks, 
Sites.Description + ',,' AS Description, Condition, 
Environment + ',,' Shafts, 
ResearchActivity + ',,' AS ResearchActivity, 
ResearcherComments + ',,' AS ResearcherComments, IsPublic, 
Active, Sites.harvardID, SiteTypes.SiteTypeID, SiteTypes.SiteType,
(ISNULL(SiteDates.EventType,'') + '_' + ISNULL(SiteDates.DateText,'')) AS SiteDates_EventType_DateText
FROM Sites 
LEFT OUTER JOIN SiteTypes ON Sites.SiteTypeID=SiteTypes.SiteTypeID AND SiteTypes.SiteTypeID != 0
LEFT OUTER JOIN SiteDates ON Sites.SiteID=SiteDates.SiteID
WHERE IsPublic = 1
ORDER BY Sites.SiteID
"""

# Alternate Numbers for Sites
ALTNUMS = """
SELECT
Sites.SiteID, AltNums.AltNum, AltNums.Description
FROM Sites 
LEFT JOIN AltNums ON Sites.SiteID=AltNums.ID AND AltNums.TableID=189
WHERE IsPublic = 1
AND AltNum IS NOT NULL
ORDER BY Sites.SiteID
"""

# Related Objects for all Sites
# TODO: Get Primary Image URL (need an image server first)
RELATED_OBJECTS = """
SELECT Sites.SiteID, SiteObjXrefs.ObjectID, 
replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.ClassificationID
FROM Sites 
LEFT JOIN SiteObjXrefs ON Sites.SiteID=SiteObjXrefs.SiteID
LEFT JOIN Objects ON SiteObjXrefs.ObjectID=Objects.ObjectID
LEFT JOIN ObjTitles ON SiteObjXrefs.ObjectID=ObjTitles.ObjectID
WHERE Sites.IsPublic = 1
AND Objects.PublicAccess = 1
ORDER BY Sites.SiteID
"""

# Related Constituents (Modern and Ancient) for all Sites
RELATED_CONSTITUENTS = """
SELECT ConXrefs.ID as SiteID, Roles.Role, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID, 
Constituents.DisplayName, Constituents.DisplayDate
FROM ConXrefs 
LEFT JOIN ConXrefDetails on ConXrefs.ConXrefID=ConXrefDetails.ConXrefID
LEFT JOIN Constituents on ConXrefDetails.ConstituentID=Constituents.ConstituentID
LEFT JOIN Roles on ConXrefs.RoleID=Roles.RoleID
WHERE ConXrefs.TableID=189
AND Constituents.Active=1
AND ConXrefDetails.Unmasked=1
ORDER BY ConXrefs.ID
"""

# Related Published Documents for all Sites 
RELATED_PUBLISHED = """
SELECT RefXrefs.ID as SiteID, ReferenceMaster.ReferenceID, ReferenceMaster.BoilerText
FROM RefXrefs 
LEFT JOIN ReferenceMaster on RefXrefs.ReferenceID=ReferenceMaster.ReferenceID
WHERE RefXrefs.TableID=189
ORDER BY RefXrefs.ID
"""

# Related Media for all Sites
RELATED_MEDIA = """
SELECT MediaXrefs.ID as SiteID, MediaMaster.MediaMasterID
FROM MediaXrefs 
LEFT JOIN MediaMaster on MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
LEFT JOIN MediaRenditions on MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
WHERE MediaXrefs.TableID=189
AND MediaMaster.PublicAccess=1
AND MediaRenditions.MediaTypeID=1
ORDER BY MediaXrefs.ID
"""