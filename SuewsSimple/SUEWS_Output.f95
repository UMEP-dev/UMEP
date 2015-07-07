!In this subroutine the output files will be opened and the output matrices will be printed out.
!
!Last change:
! HCW 27 Apr 2015
! Increased output resolution of water balance components (N.B. model time steps < 5 min may require higher precision)
! LJ in 13 April 2014
! FL in 10 June 2014
! HCW 18 Nov 2014
! LJ 5 Jan 2015: code cleaned, daily and monthly filesaving added
!-----------------------------------------------------------------------------------------------
 subroutine SUEWS_Output(Gridiv, year_int, iv, irMax)
 !INPUT: Gridiv = Grid number
 !       year_int = Year as a integer
 !       iv = Block number of met data
 !       irMax = Maximum number of rows in met data

  use sues_data
  use data_in
  use allocateArray
  use gis_data
  use time
  use defaultNotUsed
  use initial
  use solweig_module
  use cbl_module
  

  IMPLICIT NONE

  integer::i !,lfnOutC
  integer:: Gridiv, year_int, iv, irMax
  character(len=10):: str2, grstr2, yrstr2
  character(len=100):: rawpath    
    
  !================DEFINE OUTPUT FILENAME AND ITS PATH================
  write(str2,'(i2)') TSTEP/60
  write(grstr2,'(i2)') Gridiv
  write(yrstr2,'(i4)') year_int

  rawpath=trim(FileOutputPath)//trim(FileCode)//trim(adjustl(grstr2))//'_'//trim(adjustl(yrstr2))
  FileOut=trim(rawpath)//'_'//trim(adjustl(str2))//'.txt'
  SOLWEIGpoiOut=trim(rawpath)//'_SOLWEIGpoiOut.txt'
  BLOut=trim(rawpath)//'_BL.txt'
  
  !================OPEN OUTPUT FILE AND PRINT HEADER================

  ! Hourly output file
  lfnOutC=39  !Output file code

  if(iv == 1) then
    open(lfnOutC,file=trim(FileOut),err=112)
    write(lfnOutC,110)

    110 format('%iy id it imin dectime ',&
               'kdown kup ldown lup Tsurf qn h_mod e_mod qs QF QH QE ',&
               'P/i Ie/i E/i Dr/i ',&
               'St/i NWSt/i surfCh/i totCh/i ',&
               'RO/i ROsoil/i ROpipe ROpav ROveg ROwater ',&
               'AdditionalWater FlowChange WU_int WU_EveTr WU_DecTr WU_Grass ',&
               'RA RS ustar L_mod Fcld ',&
               'SoilSt smd smd_Paved smd_Bldgs smd_EveTr smd_DecTr smd_Grass smd_BSoil ',&
               'St_Paved St_Bldgs St_EveTr St_DecTr St_Grass St_BSoil St_Water ',&
               'LAI ',&
               'qn1_SF qn1_S Qm QmFreez Qmrain SWE Mw MwStore snowRem_Paved snowRem_Bldgs ChSnow/i ',&
               !'kup_Paved kup_Bldgs kup_EveTr kup_DecTr kup_Grass kup_BSoil kup_Water ',&
               !'lup_Paved lup_Bldgs lup_EveTr lup_DecTr lup_Grass lup_BSoil lup_Water ',&
               !'Ts_Paved Ts_Bldgs Ts_EveTr Ts_DecTr Ts_Grass Ts_BSoil Ts_Water ',&
               !'qn_Paved qn_Bldgs qn_EveTr qn_DecTr qn_Grass qn_BSoil qn_Water ',&
               !'SWE_Paved SWE_Bldgs SWE_EveTr SWE_DecTr SWE_Grass SWE_BSoil SWE_Water ',&
               !'Mw_Paved Mw_Bldgs Mw_EveTr Mw_DecTr Mw_Grass Mw_BSoil Mw_Water ',&
               !'Qm_Paved Qm_Bldgs Qm_EveTr Qm_DecTr Qm_Grass Qm_BSoil Qm_Water ',&
               !'Qa_Paved Qa_Bldgs Qa_EveTr Qa_DecTr Qa_Grass Qa_BSoil Qa_Water ',&
               !'QmFr_Paved QmFr_Bldgs QmFr_EveTr QmFr_DecTr QmFr_Grass QmFr_BSoil QmFr_Water ',&
               !'fr_Paved fr_Bldgs fr_EveTr fr_DecTr fr_Grass fr_BSoil ',&
               'alb_snow ')!,&
               !'RainSn_Paved RainSn_Bldgs RainSn_EveTr RainSn_DecTr RainSn_Grass RainSn_BSoil RainSn_Water ',&
               !'Qn_PavedSnow Qn_BldgsSnow Qn_EveTrSnpw Qn_DecTrSnow Qn_GrassSnpw Qn_BSoilSnow Qn_WaterSnow ',&
               !'kup_PavedSnow kup_BldgsSnow kup_EveTrSnpw kup_DecTrSnow kup_GrassSnpw kup_BSoilSnow kup_WaterSnow ',&
               !'frMelt_Paved frMelt_Bldgs frMelt_EveTr frMelt_DecTr frMelt_Grass frMelt_BSoil frMelt_Water ',&
               !'MwStore_Paved MwStore_Bldgs MwStore_EveTr MwStore_DecTr MwStore_Grass MwStore_BSoil MwStore_Water ',&
               !'DensSnow_Paved DensSnow_Bldgs DensSnow_EveTr DensSnow_DecTr DensSnow_Grass DensSnow_BSoil DensSnow_Water ',&
               !'Sd_Paved Sd_Bldgs Sd_EveTr Sd_DecTr Sd_Grass Sd_BSoil Sd_Water ',&
               !'Tsnow_Paved Tsnow_Bldgs Tsnow_EveTr Tsnow_DecTr Tsnow_Grass Tsnow_BSoil Tsnow_Water '
               !)
  else
    open(lfnOutC,file=trim(FileOut),position='append')!,err=112)
  endif

  !SOLWEIG outputfile
  if (SOLWEIGpoi_out==1) then
       open(9,file=SOLWEIGpoiOut)
       write(9,113)
  113     format('%doy dectime  azimuth altitude GlobalRad DiffuseRad DirectRad ',&
             ' Kdown2d    Kup2d    Ksouth     Kwest    Knorth     Keast ',&
             ' Ldown2d    Lup2d    Lsouth     Lwest    Lnorth     Least ',&
             '   Tmrt       I0       CI        gvf      shadow    svf    svfbuveg    Ta    Tg')
  endif
  
     !BL ouputfile
    if (CBLuse>=1)then
        open(53,file=BLOut,status='unknown')
	write(53, 102)
102  	format('iy  id   it imin dectime         z            theta          q',&
               '               theta+          q+              Temp_C          rh',&
               '              QH_use          QE_use          Press_hPa       avu1',&
               '            ustar           avdens          lv_J_kg         avcp',&
               '            gamt            gamq') 
    endif
  
 !================ACTUAL DATA WRITING================
  if (SOLWEIGpoi_out==1) then
      do i=1,SolweigCount-1
          write(9,304) int(dataOutSOL(i,1,Gridiv)),(dataOutSOL(i,is,Gridiv),is = 2,28)
      enddo
  endif  
      
  do i=1,irMax
      write(lfnoutC,301) int(dataOut(i,1,Gridiv)),int(dataOut(i,2,Gridiv)),int(dataOut(i,3,Gridiv)),int(dataOut(i,4,Gridiv)),&
                         dataOut(i,5:ncolumnsDataOut,Gridiv)
                                              
  enddo
  
if(CBLuse>=1) then
    do i=1,iCBLcount
        write(53,305)(int(dataOutBL(i,is,Gridiv)),is=1,4),(dataOutBL(i,is,Gridiv),is=5,22) 
    enddo  
endif 
  
  !================WRITING FORMAT================
  ! Main output file at model timestep
  ! Do NOT change from 301 here - read by python wrapper
  ! 301_Format           
  301 format((i4,1X),3(i3,1X),(f8.4,1X),&
             5(f9.4,1X),7(f9.4,1X),&
             4(f10.6,1X),&
             1(f10.5,1X),3(f10.6,1X),&
             6(f10.6,1X),&
             2(f9.3,1X),4(f9.4,1X),&
             3(f10.5,1X),(g14.7,1X),(f10.5,1X),&
             2(f10.4,1X),6(f10.5,1X),7(f10.4,1X),&
              (f10.4,1X),&
             5(f10.4,1X),6(f10.5,1X),&
             !14(f10.3,1X),7(f7.2,1X),7(f10.3,1X),&
             !21(f8.3,1X),&
             !14(f8.2,1X),6(f8.2,1X),&
             1(f8.4,1X))!,
             !7(f8.3,1X),14(f8.2,1X),14(f8.3,1X),14(f8.2,1X),7(f7.2,1X))             
             
             
  !==================== This part read by python wrapper ======================
  ! Update to match output columns, header and format
  ! Average, sum, or use last value to go from model timestep to 60-min output
  ! 301_Instructions         
  ! TimeCol = [1,2,3,4,5]
  ! AvCol  = [6,7,8,9,10,11,12,13,14,15,16,17,  38,39,40,41,42,  59,60,61,62,63]          
  ! SumCol = [18,19,20,21,  24,25, 26,27,28,29,30,31,  32,33,34,35,36,37,  67,68,69] 
  ! LastCol  = [22,23,  43,44,45,46,47,48,49,50,  51,52,53,54,55,56,57,  58,  64,65,66,  70]
  ! pynumformat = '%4i ' + '%3i ' * 3 + '%8.5f ' +\
  ! '%9.4f ' * 5  + '%9.4f ' * 7 +\
  ! '%10.6f ' * 4 +\
  ! '%10.5f ' * 1 + '%10.6f ' * 3 +\
  ! '%10.6f ' * 6 +\
  ! '%9.3f ' * 2  + '%9.4f ' * 4 +\
  ! '%10.5f ' * 3 + '%14.7g ' * 1 + '%10.5f ' * 1 +\
  ! '%10.4f ' * 2 + '%10.5f ' * 6 + '%10.5f ' * 7 +\
  ! '%10.4f ' * 1 +\
  ! '%10.4f ' * 5 + '%10.6f ' * 6 +\
  ! '%8.4f' * 1

  304 format(1(i3,1X),4(f8.4,1X),23(f9.3,1X))   !Solweig output
  305 format((i4,1X),3(i3,1X),(f8.4,1X),17(f15.7,1x))                              !CBL output

  !================CLOSE OUTPUTFILE================
  close (lfnoutC)
  close (9)
  close (53)
  return

  !Error commands
  112 call ErrorHint(52,trim(fileOut),notUsed,notUsed,notUsedI)


 end subroutine