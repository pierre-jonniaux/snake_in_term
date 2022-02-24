import curses , traceback , random , time , sys , os
# GLOBAL VAR
############
# la hash avec les changement de coordonnees, on pourrait faire sans,
# (p.ex. en ajoutant la valeur bool de la KEY, cad 1 ou 0 selon qu elle est pressee ou pas)
# mais je prefere comme ca. Ca pourra servir plus tard. peut etre.
directions = {\
curses.KEY_LEFT : ( 0 ,-1),\
curses.KEY_RIGHT: ( 0 , 1),\
curses.KEY_UP   : (-1 , 0),\
curses.KEY_DOWN : ( 1 , 0)\
}

# CLASSES
############
# Finalement ce serait pas mal d'avoir des variables globales genre score et autre et du coup j'en profite
# pour faire une classe dans un but purement didactique meme si justement des global var ca aurait suffit.
# Et pis c'est quand meme plus pratique y'a un seul truc a passer aux def.
class etatPartie:
    # ce truc entre 3 guillemets se nomme docstring et c'est la doc qui apparait si on tape help(etatPartie) p.ex.
    """Etat de la partie:
    - score
    - snake
    - vitesse
    - scene (trucs a afficher)"""
    def __init__(self):
        self.score = 0
        self.vitesse = 50
        self.bouffe = [0,0]
        self.seconde = 0
        self.temps = time.strftime("%H:%M:%S")
    def vitesseUp(self):
        self.vitesse = self.vitesse - 50
    def scoreUp(self):
        self.score = self.score + 25
    def setBouffe(self,y,x):
        self.bouffe = [y,x]
        
# tant que j'y suis je vais faire une classe pour le serpent et mettre
# la def de bougeage de body comme methode dedans: c'est plus mieux la classe (<- mega jeu de mot).
class serpent():
    """ Le serpent: une liste de doublets [y,x]:
    Des noms valides pour des instances de serpents sont:
    - kaa
    - plisken
    - liquid / solid
    - triste_Sire
    - nag / nagaina """
    def __init__(self,pos):
        #self.pos  = pos
        #self.pos  = pos
        #self.body = [[self.pos[0],self.pos[1]-4],[self.pos[0],self.pos[1]-3],[self.pos[0],self.pos[1]-2],[self.pos[0],self.pos[1]-1],[self.pos[0],self.pos[1]]]
        self.body = [[pos[0],pos[1]-4],[pos[0],pos[1]-3],[pos[0],pos[1]-2],[pos[0],pos[1]-1],[pos[0],pos[1]]]
    def bodyMovin(self,nextpos,grandir = False):
        self.body.append(nextpos)
        if not grandir:
            self.body.pop(0)

# cherche une "image" dans le fichier associe et en fait un objet imprimable avec une hitbox -> permet le calcul de collisions
class img():
    """Genere une image imprimable dans curses a partir d'un dessin ascii contenu dans un fichier.
    Faut:
    - le chemin du fichier
    - les ligne de debut et de fin de l'image (un fichier peut contenir plusieurs images)
    - une liste avec les variable optionelle (pour definir le nombre de barre dans la powgauge par exemple)
    Code des options: ['rev','flash',]
    'rev' = curses.A_REVERSE
    'couleur1'= paire de couleur numero1
    """
    # ouvre le fichier chaque fois: pas top. a changer
    def __init__(self,fichier,debut,fin):
        try:
            f = open(fichier, 'r')
        except:
            sys.exit('\n[ERREUR] : Pas moyen de trouver le fichier "images"\n')
        self.lines   = f.readlines()
        f.close()
        self.lines   = self.lines[debut-1:fin]
        self.largeur = max([len(l) for l in self.lines])
        self.hauteur = len(self.lines)
        # la hitbox... c'est pas facile les hitbox. c'est bien carre et ca plante souvent dans les vieux jeux les hitboxs.
        # par contre ici on travaille avec des caracteres ca va etre bcp plus simple et super precis.
        # La hitbox absolue  = une liste de position invariables (tuples) relatives a un point 0,0 qui serait le premier caractere de la 1ere ligne de l'image
        # La hitbox relative = une liste de position variables (listes a 2 item) determinant les endroits ou sont les caracteres sur l'ecran par rapport a un point de depart different de [0,0]
        # bon finalement je vais faire un systeme de hash dont les clefs sont des positions(y,x) et les valeurs le caracteres a cette position.avec ca je devrais etre pare a tous les cas de figures
        # et en tout cas ca sera bcp plus facile pour detecter les collisions a coup d'intersection de set sur les clefs de hash des sprites.
        # RM: python prend acccepte des tuples comme clef de hash mais pas des listes paske il faut des trucs invariables.
        # RM: enumerate c'est super pratique -> donne une liste de couple index-item.
        self.hitboxAbs = {}
        self.hitboxRel = {}
        y = 0
        for l in self.lines:
            for x , car in enumerate(list(l)):
                if car != ' ':
                    self.hitboxAbs[(y,x)] = car
            y = y + 1
    
    # pour afficher par string au milieu de l'ecran par defaut... redondant mais reste utile pour les titres et autres
    def afficher_par_str(self,ecr,pos,options=[]):
        """Affiche l'image si elle rentre dans le cadre sinon truncate"""    
        Y , X = ecr.getmaxyx()
        milieu = [int(round(Y-self.hauteur)/2) , int(round(X-self.largeur)/2)]
        if not pos:
            pos = milieu
        i = 0
        for l in self.lines:
            if len(options) == 2:
                ecr.addstr(pos[0]+i, pos[1],str(l),curses.A_REVERSE | curses.A_BOLD)
            elif 'rev' in options:
                ecr.addstr(pos[0]+i, pos[1],str(l),curses.A_REVERSE)
            elif 'bold' in options:
                ecr.addstr(pos[0]+i, pos[1],str(l),curses.A_BOLD)
            else:
                ecr.addstr(pos[0]+i, pos[1],str(l))
            i = i + 1
        ecr.refresh()
    
    # calcule les positions des caracteres en fonction du coin sup gauche de l'image qui est la position passee a la def
    def move_to(self,pos):
        coinDepart = tuple(pos)####
        self.hitboxRel.clear()
        for posAbsolue in self.hitboxAbs.keys():
            posRelative = tuple([sum(z)for z in zip(coinDepart,posAbsolue)])
            self.hitboxRel[posRelative] = str(self.hitboxAbs[posAbsolue])


# FONCTIONS
############

# Fonction du style bouge(ecr , pos&direction , mode) pour deplacer une position:
# - avec mode rebond, "disparition hors ecran", fuite ou poursuite
# - dans une direction numerotee facon gamefaq de jeu de baston:
# 789
# 456
# 123
# retourne un nouveau triplet [y,x,direction] en tenant compte du mode de deplacement
# A FAIRE! GERER POUR DES HITBOX ET PAS SEULEMENT DES POINTS
# -> complexe... et si je divise tout par la taille de la hitbox et que je fais comme si c'etais un gros points dans un petit carre??? ca marche ca???
# je dois donner des directions a mes objects pour qu'il les suivent, les mettre dans des liste et les updaters quand je veux
# un point c'est un triplet [y,x,direction]
# Ex: point_en_mouvement = mouvement(stdscr,[10,10,9],'rebond')
def mouvement(ecr, point , mode):
    pad = { \
    1 : ( 1 , -1),\
    2 : ( 1 ,  0),\
    3 : ( 1 ,  1),\
    4 : ( 0 , -1),\
    5 : ( 0 ,  0),\
    6 : ( 0 ,  1),\
    7 : (-1 , -1),\
    8 : (-1 ,  0),\
    9 : (-1 ,  1)\
    }
    Y , X     = ecr.getmaxyx()
    direction = point[2]
    newpoint  = [ point[0] + pad[direction][0] , point[1] + pad[direction][1] , direction]
    
    # si hors ecran et mode strict
    if (mode == 'strict') and ( newpoint[0] not in range(0,Y-1) or newpoint[1] not in range(0,X-1) ):
        newpoint = False
    # si hors ecran et mode rebond
    if (mode == 'rebond') and ( newpoint[0] not in range(0,Y-1) or newpoint[1] not in range(0,X-1) ):
        # si mouvement vertical/horizontal ou mouvement diagonal pile dans un coin -> direction opposee
        if ( direction in [2,4,6,8] ) or ( ( newpoint[0] not in range(0,Y-1) ) and ( newpoint[1] not in range(0,X-1) ) ):
            direction = 10-direction
            
        # la on passe forcement dans [1,3,7,9])
        # si mouvement diagonal touche sol/plafond
        elif newpoint[0] not in range(0,Y-1) :# and ( pad[direction] not in [2,4,6,8] ) :
            direction = direction+6 if direction in [1,3] else direction-6
            
        # si mouvement diagonal touche les murs
        elif newpoint[1] not in range(0,X-1) : # and ( pad[direction] not in [2,4,6,8] ):
            direction = direction+2 if direction in [1,7] else direction-2

        newpoint = [ point[0] + pad[direction][0] , point[1] + pad[direction][1] , direction]
    if (mode == 'poursuite'):
        pass #pour le moment
    if (mode == 'fuite'):
        pass #pour le moment
    return newpoint


# on passe a cette def un objet image contenant le dico contenant les infos de la hitbox
# aussi y va falloir definir des options (reverse, couleur..) qu'on passera comme dic
# aussi faudra gerer les collisions quelque part mais peut etre pas ici...
def affiche(stdscr,img):
    ## chaque "carxel" est donc un truc comme ca -> ( (y,x) , "caractere" )
    for carxel in img.hitboxRel.keys():
        try:
            stdscr.addstr(carxel[0], carxel[1],img.hitboxRel[carxel])
        except:
            pass
    stdscr.refresh()

# random position a l interieur du screen, parceque random.randint machin c'est log et chiant
def rpis(ecr):
    Y , X = ecr.getmaxyx()
    return(random.randint(2,Y-2),random.randint(2,X-2))

# check si la future position est toujours dans l'ecran et si oui la file
# (check aussi le coin bas-droit) sinon refile la pos initiale (et donc si newpos == oldpos ca veut dire qu'on sort de l'ecran)
def getNextPos(key,pos,ecr):
    global directions
    Y , X = ecr.getmaxyx()
    y , x = pos[0] + directions[key][0] , pos[1] + directions[key][1]
    if min(y , x)>=0 and min(Y-y-1,X-x-1)>=0 and (y , x) != (Y-1 , X-1):
        return [y , x]
    else:
        return pos

# une fois toute la scene definie on efface tout, on imprime chaque "pixel" autre que blanc, on ajoute des bordures
# a chaque fenetre et on refresh l'ecran une seule fois. Et on reinitialise la scene.
def imprime(ecr,side,snake,partie):
    ecr.erase()
    Y , X = ecr.getmaxyx()
    # d'abord la bouffe au cas ou le serpent tombe dessus
    ecr.addch(partie.bouffe[0],partie.bouffe[1],'#')
    for bodyparts in snake.body:
        ecr.addch(bodyparts[0],bodyparts[1],'o')
    side.addstr(1,1,'SCORE:')
    side.addstr(2,1,str(partie.score))
    side.addstr(4,1,'TEMPS:')
    side.addstr(5,1,str(partie.seconde))
    ecr.border()
    side.border()
    ecr.refresh()
    side.refresh()

# chope la liste des fichiers avec noms "lisibles" (cherche dans le home par defaut)
def volfichiers(rep = os.path.expanduser("~")):
    liste_fichier = []
    for repertoire, sousrepertoire , fichiers in os.walk(rep):
        for fichier in fichiers:
            if fichier and len(fichier) < 20 and re.match('.*\..*' , str(fichier)):
                liste_fichier.append(fichier)
    return liste_fichier
    
# le tres celebre ecran de game over.
# pas aussi stylay que celui de mgs sur ps et ne flash que si curses.use_default_colors()
def gameover(partie):
    gowin  = curses.newwin(0,0)
    Y , X = gowin.getmaxyx()
    #curses.flash()
    #curses.flash()
    gologo = img('./ascii-arts.txt',1,10)
    gologo.afficher_par_str(gowin,[],['bold'])
    #gowin.addstr(int(round(Y/2+2)) , int(round(X/2-5)),str('Score: '+str(partie.score)))
    #gowin.addstr(int(round(Y/2+3)) , int(round(X/2-5)),str('Temps: '+str(partie.seconde)))
    gowin.refresh()
    time.sleep(1)
    sys.exit()
    
def main(ecr):                                # le wrapper commence avec ecr comme fenetre standard de la taille du terminal
    curses.curs_set(False)                    # pas de curseur clignotant
    curses.use_default_colors()             # utilise le setup initial du terminal
    # les fenetres et leur tailles...
    Y , X = ecr.getmaxyx()                    # dimensions max de l'ecran
    ecr.resize(Y,X-15)                        # redimensionnement fenetre principal par rapport a la taille du terminal
    side  = curses.newwin(Y,14,0,X-14)        # une 2eme fenetre sur le cote
    Y , X = ecr.getmaxyx()                    # reprend les nouvelles valeurs max
    
    # initialisation des parametres du jeu...
    pos     = [int(round(Y/2)) , int(round(X/2))]        # on commence au milieu
    plisken = serpent(pos)
    partie  = etatPartie()                    # classe intialisee avec score et vitesse et temps du jeu et on set la bouffe tout de suite apres
    partie.setBouffe(random.randint(2,Y-2),random.randint(2,X-2))
    
    ecr.timeout(partie.vitesse)                # getch() attend un input et refile -1 si y'a toujours rien a la fin du delay.
    
    key = curses.KEY_RIGHT
    while (True):                            # si on a pas nodelay ou timeout le truc attend qu on appuie sur une touche
        ecr.timeout(partie.vitesse)
        if partie.temps != time.strftime("%H:%M:%S"):
            partie.temps = time.strftime("%H:%M:%S")
            partie.seconde = partie.seconde + 1
        event = ecr.getch()
        key = key if event == -1 else event
        if key == 27:                        # 27 = ascii code touche escape
            break
        if key in directions.keys():
            nextpos = getNextPos(key,pos,ecr)
            if ( nextpos != pos ) and ( nextpos not in plisken.body):
                if nextpos == partie.bouffe:
                    plisken.bodyMovin(nextpos,True)
                    partie.setBouffe(random.randint(2,Y-2),random.randint(2,X-2))
                    partie.scoreUp()
                    partie.vitesseUp()
                else:
                    plisken.bodyMovin(nextpos)
                pos = nextpos
                imprime(ecr,side,plisken,partie)
            else:
                gameover(partie)

# un wrapper deja tout fait qui garanti une sortie propre de curse en cas de merdouille
curses.wrapper(main)            
