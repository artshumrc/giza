DRS = {
     """
     SELECT DISTINCT ArchIDNum AS ArchIDNum FROM MediaFiles ORDER BY ArchIDNum ASC
     """
}

SQL = {
     'iiif' : {
          'iiif' : """
               SELECT MediaMaster.MediaMasterID AS RecID, MediaRenditions.MediaTypeID, MediaRenditions.RenditionNumber,
               replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description, MediaMaster.MediaView,
               replace(replace(MediaMaster.PublicCaption, char(10), ''), char(13), ' ') AS PublicCaption,
               MediaFiles.ArchIDNum, Departments.Department, replace(replace(Date.TextEntry, char(10), ''), char(13), ' ') AS DateOfCapture, replace(replace(Problems.TextEntry, char(10), ''), char(13), ' ') AS ProblemsQuestions
               FROM MediaMaster
               LEFT JOIN Departments ON MediaMaster.DepartmentID=Departments.DepartmentID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN TextEntries AS Date ON MediaMaster.MediaMasterID=Date.ID AND Date.TableID=318 AND Date.TextTypeID=3
               LEFT JOIN TextEntries AS Problems ON MediaMaster.MediaMasterID=Problems.ID AND Problems.TableID=318 AND Problems.TextTypeID=5
               WHERE MediaMaster.PublicAccess=1
               AND (MediaRenditions.PrimaryFileID = -1 OR MediaRenditions.PrimaryFileID=MediaFiles.FileID)
               AND MediaFiles.ArchIDNum IS NOT NULL
               ORDER BY MediaMaster.MediaMasterID
               """,
          'iiif_photographers' : """
               SELECT DISTINCT MediaMaster.MediaMasterID AS RecID, MediaRenditions.MediaTypeID, Roles.Role, Constituents.DisplayName, Constituents.DisplayDate
               FROM MediaMaster
               JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
               JOIN ConXrefs on MediaRenditions.RenditionID=ConXrefs.ID AND ConXrefs.TableID=322
               JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
               JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
               WHERE MediaMaster.PublicAccess=1
               AND Roles.RoleID = 11
               ORDER BY MediaMaster.MediaMasterID
               """
     },
     'met' : {
          'met' : """
               SELECT tm.DateEntered, t.Term, t.TermID, replace(NodeDepth, NodeDepth, NodeDepth-3) AS NodeDepth, substring(tm.CN, 13, 50) AS CN
               FROM gizaCARDTMSThes_2.dbo.Terms t
               JOIN gizaCARDTMSThes_2.dbo.TermMaster tm ON tm.TermMasterID=t.TermMasterID
               WHERE CN LIKE 'AUT.AAA.AAK%'
               ORDER BY NodeDepth ASC
          """,
          'xrefs' : """
               SELECT x.ID AS MediaMasterID, t.Term, t.TermID, replace(NodeDepth, NodeDepth, NodeDepth-3) AS NodeDepth, substring(tm.CN, 13, 50) AS CN
               FROM gizaCARDTMSThes_2.dbo.Terms t
               JOIN gizaCARDTMSThes_2.dbo.TermMaster tm ON tm.TermMasterID=t.TermMasterID
               JOIN gizaCARDTMS_2.dbo.ThesXrefs x ON x.TermID=t.TermID
               WHERE NodeDepth > 2 AND CN LIKE 'AUT.AAA%'
               ORDER By MediaMasterID ASC
          """
     },
     'sites': {
         'sites': 
               """
               SELECT Sites.SiteID AS RecID, SiteName, SiteNumber AS Number, SiteSortNumber, HistoricalNotes,
               LegalNotes + ',,' AS BibReferences, LocationNotes,
               Sites.Remarks + ',,' AS Remarks,
               Sites.Description + ',,' AS Description, Condition,
               Environment + ',,' Shafts,
               ResearchActivity + ',,' AS ResearchActivity,
               ResearcherComments + ',,' AS ResearcherComments, IsPublic,
               Active, Sites.harvardID, SiteTypes.SiteTypeID, SiteTypes.SiteType, TextEntries.TextEntry AS ProblemsQuestions
               FROM Sites
               LEFT OUTER JOIN SiteTypes ON Sites.SiteTypeID=SiteTypes.SiteTypeID AND SiteTypes.SiteTypeID != 0
               LEFT JOIN TextEntries ON Sites.SiteID=TextEntries.ID AND TextEntries.TableID=189 AND TextEntries.TextTypeID=1
               WHERE IsPublic = 1
               ORDER BY Sites.SiteID
               """,
          'sites_dates': 
               """
               SELECT Sites.SiteID AS RecID, SiteDates.EventType, SiteDates.DateText
               FROM Sites
               JOIN SiteDates ON Sites.SiteID=SiteDates.SiteID
               WHERE Sites.IsPublic=1
               ORDER BY Sites.SiteID
               """,
          'sites_altnums': 
               """
               SELECT Sites.SiteID AS RecID, AltNums.AltNum, AltNums.Description
               FROM Sites
               LEFT JOIN AltNums ON Sites.SiteID=AltNums.ID AND AltNums.TableID=189
               WHERE IsPublic = 1
               AND AltNum IS NOT NULL
               ORDER BY Sites.SiteID
               """,
          'sites_objects':
               """
               SELECT DISTINCT Sites.SiteID AS RecID, SiteObjXrefs.ObjectID,
               replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated AS ObjectDate,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM Sites
               JOIN SiteObjXrefs ON Sites.SiteID=SiteObjXrefs.SiteID
               JOIN Objects ON SiteObjXrefs.ObjectID=Objects.ObjectID AND Objects.PublicAccess=1
               LEFT JOIN ObjTitles ON SiteObjXrefs.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
               LEFT JOIN MediaXrefs ON Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.TableID=108 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE Sites.IsPublic = 1
               AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY Sites.SiteID, SiteObjXrefs.ObjectID
               """,
          'sites_constituents':
               """
               SELECT DISTINCT ConXrefs.ID AS RecID, Roles.Role, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
               Constituents.DisplayName, Constituents.DisplayDate, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM ConXrefs
               INNER JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               INNER JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1
               INNER JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
               INNER JOIN Sites ON ConXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
               LEFT JOIN MediaXrefs ON Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE ConXrefs.TableID=189
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY ConXrefs.ID
               """, 
          'sites_published': 
               """
               SELECT DISTINCT RefXrefs.ID AS RecID, ReferenceMaster.ReferenceID, ReferenceMaster.Title,
               ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
               FROM Sites
               JOIN RefXRefs ON Sites.SiteID=RefXRefs.ID
               JOIN ReferenceMaster ON RefXRefs.ReferenceID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
               LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
               AND MediaTypeID=4
               AND Sites.IsPublic=1
               ORDER BY RecID, ReferenceMaster.ReferenceID
               """,
          'sites_media': 
               """
               SELECT DISTINCT MediaXrefs.ID AS RecID, MediaMaster.MediaMasterID AS RecID, MediaXrefs.PrimaryDisplay,
               MediaRenditions.MediaTypeID, MediaRenditions.RenditionNumber, replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description,
               MediaMaster.MediaView, MediaMaster.PublicCaption,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName, MediaFiles.ArchIDNum
               FROM MediaXrefs
               INNER JOIN Sites ON MediaXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE MediaXrefs.TableID=189
               AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
               ORDER BY MediaXrefs.ID, MediaMaster.MediaMasterID
               """
     },
     'objects' : {
          'objects' : 
               """
               SELECT Objects.ObjectID AS RecID, Objects.ObjectNumber AS Number, Objects.ObjectStatusID, Objects.ClassificationID,
               (Classifications.Classification + ISNULL(('-' + Classifications.SubClassification),'')) AS ClassificationText,
               Objects.ObjectName + ',,' AS ObjectOwnerDetails, Departments.Department, ObjContext.Period,
               Objects.Dated AS EntryDate, replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.Medium + ',,' AS Medium,
               Objects.Dimensions + ',,' AS Dimensions, Objects.CreditLine, Objects.Description + ',,' AS Description, Objects.Provenance,
               Objects.PubReferences + ',,' AS BibReferences, Objects.Notes + ',,' AS Notes, Objects.Chat + ',,' AS DiaryTranscription,
               Objects.CuratorialRemarks + ',,' AS Remarks, TextEntries.TextEntry AS ProblemsQuestions
               FROM Objects
               LEFT JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
               LEFT JOIN Classifications ON Objects.ClassificationID=Classifications.ClassificationID
               LEFT JOIN Departments ON Objects.DepartmentID=Departments.DepartmentID
               LEFT JOIN ObjContext ON Objects.ObjectID=ObjContext.ObjectID
               LEFT JOIN TextEntries ON Objects.ObjectID=TextEntries.ID AND TextEntries.TableID=108 AND TextEntries.TextTypeID=12
               WHERE Objects.PublicAccess = 1
               AND Objects.ObjectID >= 0
               ORDER BY Objects.ObjectID
               """,
          'objects_geocodes' :
               """
               SELECT ObjGeography.ObjectID AS RecID, ObjGeography.GeoCodeID, GeoCodes.GeoCode, ObjGeography.Region, ObjGeography.City, Objects.ClassificationID
               FROM ObjGeography
               JOIN GeoCodes ON ObjGeography.GeoCodeID=GeoCodes.GeoCodeID
               JOIN Objects ON ObjGeography.ObjectID=Objects.ObjectID AND Objects.PublicAccess=1
               WHERE ObjGeography.ObjectID >= 0
               AND ObjGeography.GeoCodeID > 0
               """,
          'objects_altnums' :
               """
               SELECT Objects.ObjectID AS RecID, Objects.ClassificationID, AltNums.AltNum, AltNums.Description
               FROM Objects
               LEFT JOIN AltNums ON Objects.ObjectID=AltNums.ID AND AltNums.TableID=108
               WHERE Objects.PublicAccess = 1
               AND AltNums.AltNum IS NOT NULL
               AND AltNums.Description != 'Artemis_ObjectID'
               ORDER BY Objects.ObjectID
               """,
          'objects_flexfields' :
               """
               SELECT Objects.ObjectID AS RecID, Objects.ClassificationID, UserFieldGroups.GroupName, UserFields.UserFieldName,
               UserFieldXrefs.FieldValue
               FROM UserFieldXrefs
               JOIN UserFields ON UserFieldXrefs.UserFieldID=UserFields.UserFieldID
               JOIN UserFieldGroups ON UserFieldXrefs.UserFieldGroupID=UserFieldGroups.UserFieldGroupID
               JOIN Objects ON UserFieldXrefs.ID=Objects.ObjectID AND Objects.ClassificationID=83
               WHERE UserFieldXrefs.FieldValue != '(not assigned)'
               ORDER BY Objects.ObjectID
               """,
          'objects_sites' : 
               """
               SELECT DISTINCT Objects.ObjectID AS RecID, SiteObjXrefs.SiteID,
               Sites.SiteName, Sites.SiteNumber, Objects.ClassificationID,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM Objects
               JOIN SiteObjXrefs ON Objects.ObjectID=SiteObjXrefs.ObjectID
               JOIN Sites ON SiteObjXrefs.SiteID=Sites.SiteID AND Sites.IsPublic = 1
               LEFT JOIN MediaXrefs ON Sites.SiteID=MediaXrefs.ID AND MediaXrefs.TableID=189 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE Objects.PublicAccess = 1
               AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY Objects.ObjectID, SiteObjXrefs.SiteID
               """,
          'objects_constituents' :
               """
               SELECT DISTINCT ConXrefs.ID AS RecID, Roles.Role, Roles.RoleID, ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID,
               Constituents.DisplayName, Constituents.DisplayDate, Objects.ClassificationID, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM ConXrefs
               INNER JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               INNER JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.Active=1
               INNER JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
               INNER JOIN Objects ON ConXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
               LEFT JOIN MediaXrefs ON Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE ConXrefs.TableID=108
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY ConXrefs.ID, ConXrefDetails.ConstituentID
               """,
          'objects_published' : 
               """
               SELECT RefXrefs.ID AS RecID, ReferenceMaster.ReferenceID, ReferenceMaster.Title, ReferenceMaster.BoilerText,
               Objects.ClassificationID, ReferenceMaster.DisplayDate,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
               FROM Objects
               JOIN RefXRefs ON Objects.ObjectID=RefXRefs.ID
               JOIN ReferenceMaster ON RefXrefs.ReferenceID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
               JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.TableID=143 AND MediaXrefs.PrimaryDisplay=1
               JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
               JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
               AND MediaTypeID=4
               AND Objects.PublicAccess=1
               ORDER BY Objects.ObjectID, ReferenceMaster.ReferenceID
               """,
          'objects_unpublished' : 
               """
               SELECT DISTINCT Associations.ID1 AS RecID, Associations.ID2 AS UnpublishedID, Objects.ObjectNumber,
               replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS UnpublishedTitle, Objects.ClassificationID, Objects.Dated AS ObjectDate,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM Associations
               LEFT JOIN ObjTitles ON Associations.ID2=ObjTitles.ObjectID
               LEFT JOIN Objects ON Associations.ID1=Objects.ObjectID AND Objects.PublicAccess=1
               LEFT JOIN MediaXrefs ON Associations.ID2=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE Associations.TableID=108
               AND RelationshipID=6
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY ID1, Associations.ID2
               """,
          'objects_media' :
               """
               SELECT MediaXrefs.ID AS ID, MediaMaster.MediaMasterID AS RecID, Objects.ClassificationID, MediaXrefs.PrimaryDisplay,
               MediaRenditions.MediaTypeID, MediaRenditions.RenditionNumber, replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description,
               MediaMaster.MediaView, replace(replace(MediaMaster.PublicCaption, char(10), ''), char(13), ' ') AS PublicCaption,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName, MediaFiles.ArchIDNum
               FROM MediaXrefs
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               JOIN Objects ON MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE MediaXrefs.TableID=108
               AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
               ORDER BY MediaXrefs.ID, MediaMaster.MediaMasterID
               """
     },
     'constituents' : {
          'constituents' : """
               SELECT DISTINCT Constituents.ConstituentID AS RecID, Constituents.DisplayName, Constituents.DisplayDate,
               Constituents.ConstituentTypeID, ConTypes.ConstituentType, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks, Terms.Term AS Gender,
               Constituents.Institution, Constituents.Nationality, Constituents.BeginDate, Constituents.EndDate
               FROM Constituents
               LEFT JOIN ConXrefDetails ON Constituents.ConstituentID=ConXrefDetails.ConstituentID AND ConXrefDetails.UnMasked=1
               LEFT JOIN ConTypes ON Constituents.ConstituentTypeID=ConTypes.ConstituentTypeID
               LEFT JOIN ThesXrefs ON Constituents.ConstituentID=ThesXrefs.ID AND ThesXrefs.ThesXrefTypeID=2 AND ThesXrefs.TableID=23
               LEFT JOIN ThesXrefTypes ON ThesXrefs.ThesXrefTypeID=ThesXrefTypes.ThesXrefTypeID
               LEFT JOIN gizaCARDTMSThes_2.dbo.Terms Terms ON ThesXrefs.TermID=Terms.TermID
               WHERE Constituents.PublicAccess=1
               AND Constituents.ConstituentTypeID>0
               ORDER BY Constituents.ConstituentID
               """,
          'constituents_altnames' : """
               SELECT Constituents.ConstituentID AS RecID, Constituents.ConstituentTypeID, ConAltNames.DisplayName, ConAltNames.NameType
               FROM Constituents
               LEFT JOIN ConAltNames ON Constituents.ConstituentID=ConAltNames.ConstituentID
               WHERE Constituents.PublicAccess=1
               AND Constituents.ConstituentTypeID>0
               AND NameType != 'Primary Name'
               ORDER BY Constituents.ConstituentID
               """,
          'constituents_objects' : """
               SELECT DISTINCT Constituents.ConstituentID AS RecID, Constituents.ConstituentTypeID, ConXrefs.ID AS ObjectID, replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber,
               Objects.ClassificationID, Objects.Dated AS ObjectDate,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM ConXrefs
               JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0 AND Constituents.Active=1
               JOIN Objects ON ConXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
               JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
               LEFT JOIN MediaXrefs ON Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.TableID=108 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE ConXrefs.TableID=108
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY Constituents.ConstituentID, ConXrefs.ID
               """,
          'constituents_sites' : """
               SELECT DISTINCT Constituents.ConstituentID AS RecID, Constituents.ConstituentTypeID, ConXrefs.ID AS SiteID, Sites.SiteName, Sites.SiteNumber,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM ConXrefs
               JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0 AND Constituents.Active=1
               JOIN Sites ON ConXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
               LEFT JOIN MediaXrefs ON Sites.SiteID=MediaXrefs.ID AND MediaXrefs.TableID=189 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE ConXrefs.TableID=189
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY Constituents.ConstituentID, ConXrefs.ID
               """,
          'constituents_published' : """
               SELECT DISTINCT Constituents.ConstituentID AS RecID, Constituents.ConstituentTypeID, ReferenceMaster.ReferenceID, ReferenceMaster.Title, ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
               FROM ConXrefs
               JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
               JOIN ReferenceMaster ON ConXrefs.ID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
               LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.TableID=143 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE ConXrefs.TableID=143
               AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
               AND MediaTypeID=4
               ORDER BY Constituents.ConstituentID
               """,
          'constituents_media' : """
               SELECT DISTINCT MediaXrefs.ID AS RecID, Constituents.ConstituentTypeID,  MediaMaster.MediaMasterID, Objects.ClassificationID, MediaXrefs.PrimaryDisplay,
               MediaRenditions.MediaTypeID, MediaRenditions.RenditionNumber, replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description,
               MediaMaster.MediaView, replace(replace(MediaMaster.PublicCaption, char(10), ''), char(13), ' ') AS PublicCaption,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName, MediaFiles.ArchIDNum
               FROM MediaXrefs
               JOIN Constituents ON MediaXrefs.ID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN Objects ON MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE MediaXrefs.TableID=23
               AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
               ORDER BY MediaXrefs.ID, MediaMaster.MediaMasterID
               """
     },
     'published' : {
          'published' : """
               SELECT ReferenceMaster.ReferenceID AS RecID, ReferenceMaster.Title, ReferenceMaster.Notes,
               ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate, ReferenceMaster.YearPublished,
               RefFormats.Format, Languages.Language, ReferenceMaster.NumOfPages,
               ReferenceMaster.Journal, ReferenceMaster.Series
               FROM ReferenceMaster
               LEFT JOIN Languages ON ReferenceMaster.LanguageID=Languages.LanguageID
               LEFT JOIN RefFormats ON ReferenceMaster.FormatID=RefFormats.FormatID
               WHERE ReferenceMaster.PublicAccess=1
               ORDER BY ReferenceMaster.ReferenceID
               """,
          'published_sites' : """
               SELECT DISTINCT ReferenceMaster.ReferenceID AS RecID, RefXrefs.ID AS SiteID, Sites.SiteName, Sites.SiteNumber,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM ReferenceMaster
               JOIN RefXRefs ON ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=189
               JOIN Sites ON Sites.SiteID=RefXRefs.ID AND Sites.IsPublic=1
               LEFT JOIN MediaXrefs ON Sites.SiteID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=189
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE ReferenceMaster.PublicAccess=1
               AND (
               (ThumbPath.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (ThumbPath.Path LIKE 'Y:%')
               OR (ThumbPath.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY ReferenceMaster.ReferenceID, RefXrefs.ID
               """,
          'published_objects' : """
               SELECT DISTINCT ReferenceMaster.ReferenceID AS RecID, RefXrefs.ID AS ObjectID,
               replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.ClassificationID, Objects.Dated AS ObjectDate,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM ReferenceMaster
               JOIN RefXRefs ON ReferenceMaster.ReferenceID=RefXRefs.ReferenceID AND RefXRefs.TableID=108
               JOIN Objects ON Objects.ObjectID=RefXRefs.ID AND Objects.PublicAccess=1
               JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
               LEFT JOIN MediaXrefs ON Objects.ObjectID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE ReferenceMaster.PublicAccess=1
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY ReferenceMaster.ReferenceID, RefXrefs.ID
               """,
          'published_constituents' : """
               SELECT DISTINCT ReferenceMaster.ReferenceID AS RecID,
               ConXrefDetails.ConstituentID, Constituents.ConstituentTypeID, Roles.Role,
               Constituents.DisplayName, Constituents.DisplayDate, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks, Constituents.AlphaSort,
               MediaPaths.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               from ReferenceMaster
               INNER JOIN ConXrefs ON ReferenceMaster.ReferenceID=ConXrefs.ID AND ConXrefs.TableID=143
               INNER JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               INNER JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
               INNER JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
               LEFT JOIN MediaXrefs ON Constituents.ConstituentID=MediaXrefs.ID AND MediaXrefs.TableID=23 AND MediaXrefs.PrimaryDisplay=1
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaPaths ON MediaRenditions.ThumbPathID=MediaPaths.PathID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               WHERE ReferenceMaster.PublicAccess=1
               AND (
               (MediaPaths.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (MediaPaths.Path LIKE 'Y:%')
               OR (MediaPaths.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY ReferenceMaster.ReferenceID, ConXrefDetails.ConstituentID
               """,
          'published_media' : """
               SELECT ReferenceMaster.ReferenceID AS RecID, MediaMaster.MediaMasterID,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
               FROM ReferenceMaster
               LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
               LEFT JOIN MediaMaster ON MediaXrefs.MediaMasterID=MediaMaster.MediaMasterID AND MediaMaster.PublicAccess=1
               LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID=4
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID AND MediaRenditions.PrimaryFileID=MediaFiles.FileID
               LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE MediaFiles.FileName IS NOT NULL
               AND ReferenceMaster.PublicAccess=1
               ORDER BY ReferenceMaster.ReferenceID
               """
     },
     'media' : {
          'media' : """
               SELECT MediaMaster.MediaMasterID AS RecID, MediaRenditions.RenditionNumber, MediaRenditions.MediaTypeID, MediaRenditions.PrimaryFileID,
               replace(replace(MediaMaster.Description, char(10), ''), char(13), ' ') AS Description, MediaMaster.MediaView,
               replace(replace(MediaMaster.PublicCaption, char(10), ''), char(13), ' ') AS PublicCaption,
               replace(replace(MediaRenditions.Remarks, char(10), ''), char(13), ' ') AS Remarks,
               Departments.Department,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName, MediaFiles.ArchIDNum,
               replace(replace(Date.TextEntry, char(10), ''), char(13), ' ') AS DateOfCapture, replace(replace(Problems.TextEntry, char(10), ''), char(13), ' ') AS ProblemsQuestions
               FROM MediaMaster
               LEFT JOIN Departments ON MediaMaster.DepartmentID=Departments.DepartmentID
               LEFT JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS ThumbPath ON MediaRenditions.ThumbPathID=ThumbPath.PathID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               LEFT JOIN TextEntries AS Date ON MediaMaster.MediaMasterID=Date.ID AND Date.TableID=318 AND Date.TextTypeID=3
               LEFT JOIN TextEntries AS Problems ON MediaMaster.MediaMasterID=Problems.ID AND Problems.TableID=318 AND Problems.TextTypeID=5
               WHERE MediaMaster.PublicAccess=1
               AND (MediaRenditions.PrimaryFileID = -1 OR MediaRenditions.PrimaryFileID=MediaFiles.FileID)
               ORDER BY MediaMaster.MediaMasterID
               """,
          'media_photographers' : """
               SELECT DISTINCT MediaMaster.MediaMasterID AS RecID, MediaRenditions.MediaTypeID, Roles.Role, Constituents.DisplayName, Constituents.DisplayDate
               FROM MediaMaster
               JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
               JOIN ConXrefs on MediaRenditions.RenditionID=ConXrefs.ID AND ConXrefs.TableID=322
               JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
               JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
               WHERE MediaMaster.PublicAccess=1
               AND Roles.RoleID = 11
               ORDER BY MediaMaster.MediaMasterID
               """,
          'media_sites' : """
               SELECT DISTINCT MediaMaster.MediaMasterID AS RecID, MediaXrefs.ID AS SiteID, MediaRenditions.MediaTypeID,
               Sites.SiteName, Sites.SiteNumber, Sites.Description + ',,' AS Description,
               ThumbPath.Path AS ThumbPathName, SiteRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM MediaMaster
               JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
               JOIN MediaXrefs ON MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=189
               JOIN Sites ON MediaXrefs.ID=Sites.SiteID AND Sites.IsPublic=1
               LEFT JOIN MediaXrefs AS SiteXrefs ON Sites.SiteID=SiteXrefs.ID AND SiteXrefs.PrimaryDisplay=1 AND SiteXrefs.TableID=189
               LEFT JOIN MediaMaster AS SiteMaster ON SiteXrefs.MediaMasterID=SiteMaster.MediaMasterID AND SiteMaster.PublicAccess=1
               LEFT JOIN MediaRenditions AS SiteRenditions ON SiteMaster.MediaMasterID=SiteRenditions.MediaMasterID
               LEFT JOIN MediaFiles ON SiteRenditions.RenditionID=MediaFiles.RenditionID AND SiteRenditions.PrimaryFileID=MediaFiles.FileID
               LEFT JOIN MediaPaths AS ThumbPath ON SiteRenditions.ThumbPathID=ThumbPath.PathID
               WHERE MediaMaster.PublicAccess=1
               AND (
               (ThumbPath.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (ThumbPath.Path LIKE 'Y:%')
               OR (ThumbPath.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY MediaMaster.MediaMasterID, MediaXrefs.ID
               """,
          'media_objects' : """
               SELECT DISTINCT MediaMaster.MediaMasterID AS RecID, MediaRenditions.MediaTypeID, MediaXrefs.ID AS ObjectID, Objects.ClassificationID,
               replace(replace(ObjTitles.Title, char(10), ''), char(13), ' ') AS Title, Objects.ObjectNumber, Objects.Dated AS ObjectDate,
               ThumbPath.Path AS ThumbPathName, ObjectRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM MediaMaster
               JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
               JOIN MediaXrefs ON MediaMaster.MediaMasterID=MediaXrefs.MediaMasterID AND MediaXrefs.TableID=108
               JOIN Objects ON MediaXrefs.ID=Objects.ObjectID AND Objects.PublicAccess=1
               JOIN ObjTitles ON Objects.ObjectID=ObjTitles.ObjectID AND ObjTitles.DisplayOrder=1
               LEFT JOIN MediaXrefs AS ObjectXrefs ON Objects.ObjectID=ObjectXrefs.ID AND ObjectXrefs.PrimaryDisplay=1 AND ObjectXrefs.TableID=108
               LEFT JOIN MediaMaster AS ObjectMaster ON ObjectXrefs.MediaMasterID=ObjectMaster.MediaMasterID AND ObjectMaster.PublicAccess=1
               LEFT JOIN MediaRenditions AS ObjectRenditions ON ObjectMaster.MediaMasterID=ObjectRenditions.MediaMasterID
               LEFT JOIN MediaFiles ON ObjectRenditions.RenditionID=MediaFiles.RenditionID AND ObjectRenditions.PrimaryFileID=MediaFiles.FileID
               LEFT JOIN MediaPaths AS ThumbPath ON ObjectRenditions.ThumbPathID=ThumbPath.PathID
               WHERE MediaMaster.PublicAccess=1
               AND (
               (ThumbPath.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (ThumbPath.Path LIKE 'Y:%')
               OR (ThumbPath.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY MediaMaster.MediaMasterID, MediaXrefs.ID
               """,
          'media_constituents' : """
               SELECT DISTINCT MediaMaster.MediaMasterID AS RecID, MediaRenditions.MediaTypeID, Constituents.ConstituentID, Constituents.ConstituentTypeID,
               Roles.Role, Roles.RoleID,
               Constituents.DisplayName, Constituents.DisplayDate, replace(replace(Constituents.Remarks, char(10), ''), char(13), ' ') AS Remarks,
               ThumbPath.Path AS ThumbPathName, MediaRenditions.ThumbFileName, MediaFiles.ArchIDNum
               FROM MediaMaster
               JOIN MediaRenditions ON MediaMaster.MediaMasterID=MediaRenditions.MediaMasterID AND MediaRenditions.MediaTypeID IS NOT NULL AND MediaRenditions.MediaTypeID != 4
               JOIN ConXrefs on MediaRenditions.RenditionID=ConXrefs.ID AND ConXrefs.TableID=322
               JOIN ConXrefDetails ON ConXrefs.ConXrefID=ConXrefDetails.ConXrefID AND ConXrefDetails.Unmasked=1
               JOIN Constituents ON ConXrefDetails.ConstituentID=Constituents.ConstituentID AND Constituents.PublicAccess=1 AND Constituents.ConstituentTypeID>0
               JOIN Roles ON ConXrefs.RoleID=Roles.RoleID
               LEFT JOIN MediaXrefs AS ConstituentXrefs ON Constituents.ConstituentID=ConstituentXrefs.ID AND ConstituentXrefs.PrimaryDisplay=1 AND ConstituentXrefs.TableID=23
               LEFT JOIN MediaMaster AS ConstituentMaster ON ConstituentXrefs.MediaMasterID=ConstituentMaster.MediaMasterID AND ConstituentMaster.PublicAccess=1
               LEFT JOIN MediaRenditions AS ConstituentRenditions ON ConstituentMaster.MediaMasterID=ConstituentRenditions.MediaMasterID
               LEFT JOIN MediaFiles ON ConstituentRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS ThumbPath ON ConstituentRenditions.ThumbPathID=ThumbPath.PathID
               WHERE MediaMaster.PublicAccess=1
               AND (
               (ThumbPath.Path IS NOT NULL AND MediaRenditions.ThumbFileName IS NOT NULL AND MediaFiles.ArchIDNum IS NOT NULL)
               OR (ThumbPath.Path LIKE 'Y:%')
               OR (ThumbPath.Path IS NUll AND MediaRenditions.ThumbFileName IS NULL AND MediaFiles.ArchIDNum IS NULL))
               ORDER BY MediaMaster.MediaMasterID
               """,
          'media_published' : """
               SELECT RefXrefs.ID AS RecID, MasterRenditions.MediaTypeID, ReferenceMaster.ReferenceID, ReferenceMaster.Title,
               ReferenceMaster.BoilerText, ReferenceMaster.DisplayDate,
               MainPath.Path AS MainPathName, MediaFiles.FileName AS MainFileName
               FROM MediaMaster
               JOIN MediaRenditions AS MasterRenditions ON MediaMaster.MediaMasterID=MasterRenditions.MediaMasterID
               JOIN RefXRefs ON MediaMaster.MediaMasterID=RefXRefs.ID
               JOIN ReferenceMaster ON RefXRefs.ReferenceID=ReferenceMaster.ReferenceID AND ReferenceMaster.PublicAccess=1
               LEFT JOIN MediaXrefs ON ReferenceMaster.ReferenceID=MediaXrefs.ID AND MediaXrefs.PrimaryDisplay=1 AND MediaXrefs.TableID=143
               LEFT JOIN MediaRenditions ON MediaXrefs.MediaMasterID=MediaRenditions.MediaMasterID
               LEFT JOIN MediaFiles ON MediaRenditions.RenditionID=MediaFiles.RenditionID
               LEFT JOIN MediaPaths AS MainPath ON MediaFiles.PathID=MainPath.PathID
               WHERE MediaRenditions.PrimaryFileID=MediaFiles.FileID
               AND MediaRenditions.MediaTypeID=4
               AND MediaMaster.PublicAccess=1
               ORDER BY MediaMaster.MediaMasterID, ReferenceMaster.ReferenceID
               """
     }
}